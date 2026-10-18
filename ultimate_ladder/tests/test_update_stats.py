"""Tests of the scores (OpenSkill ratings, see rating.py) and of the
statistics of the players, updated when a game is completed."""
import random
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from ultimate_ladder import rating
from ultimate_ladder.models import Player, PlayerStats
from ultimate_ladder.views import TeamScore, UpdateStats

from .utils import make_game, make_league, make_player, make_user


class RatingTestCase(TestCase):
    def setUp(self):
        self.user = make_user()
        self.league = make_league(self.user)

    def players(self, *scores, prefix="P"):
        players = []
        for i, s in enumerate(scores):
            p = make_player(self.user, f"{prefix}{i}-{s}", score=s)
            p.initial_score = s
            rating.reset_player(p)
            p.save()
            players.append(p)
        return players

    def play(self, team_a, team_b, score_a, score_b, league=None):
        game = make_game(league or self.league, team_a, team_b)
        game.score_team_a = score_a
        game.score_team_b = score_b
        game.completed = True
        game.completion_date = timezone.now()
        game.save()
        UpdateStats(game)
        for p in team_a + team_b:
            p.refresh_from_db()
        return game

    def stats(self, player, league=None):
        return PlayerStats.objects.get(player=player, league=league or self.league)


class DisplayScoreTests(TestCase):
    def test_new_player_starts_at_1000(self):
        self.assertEqual(rating.display_score(*rating.initial_rating(1000)), 1000)

    def test_initial_rating_matches_the_displayed_score(self):
        for score in [400, 800, 1000, 1234, 1600]:
            self.assertEqual(rating.display_score(*rating.initial_rating(score)), score)

    def test_reset_player(self):
        p = Player(initial_score=1300)
        rating.reset_player(p)
        self.assertEqual(p.score, 1300)
        self.assertEqual(p.sigma, rating.MODEL.sigma)


class UpdateStatsTests(RatingTestCase):
    def test_team_score(self):
        a = self.players(1000, 1200)
        game = make_game(self.league, a, [])
        self.assertEqual(TeamScore(game.team_set.filter(team_name="A")), 2200)

    def test_winners_gain_and_losers_lose(self):
        a = self.players(1000, 1000)
        b = self.players(1000, 1000, prefix="Q")
        self.play(a, b, 5, 3)
        gain = a[0].score - 1000
        self.assertGreater(gain, 0)
        for p in a:
            self.assertEqual(p.score, 1000 + gain)
        # between teams of the same level, the losers lose what the winners gain
        for p in b:
            self.assertEqual(p.score, 1000 - gain)

    def test_team_b_wins(self):
        a = self.players(1000, 1000)
        b = self.players(1000, 1000, prefix="Q")
        self.play(a, b, 3, 5)
        self.assertLess(a[0].score, 1000)
        self.assertGreater(b[0].score, 1000)

    def test_draw_between_teams_of_the_same_level(self):
        a = self.players(1100, 900)
        b = self.players(1000, 1000, prefix="Q")
        self.play(a, b, 4, 4)
        self.assertEqual([p.score for p in a + b], [1100, 900, 1000, 1000])
        # ... but the uncertainty decreases
        self.assertLess(a[0].sigma, rating.MODEL.sigma)

    def test_draw_against_a_stronger_team_is_a_good_result(self):
        a = self.players(1200, 1200)
        b = self.players(900, 900, prefix="Q")
        self.play(a, b, 4, 4)
        self.assertLess(a[0].score, 1200)
        self.assertGreater(b[0].score, 900)

    def test_only_the_result_matters(self):
        close = self.players(1000, 1000) + self.players(1000, 1000, prefix="Q")
        large = self.players(1000, 1000, prefix="R") + self.players(1000, 1000, prefix="S")
        self.play(close[:2], close[2:], 7, 6)
        self.play(large[:2], large[2:], 15, 0)
        self.assertEqual([p.score for p in close], [p.score for p in large])

    def test_beating_a_stronger_team_gives_more_points(self):
        weak, strong = self.players(900, 900), self.players(1100, 1100, prefix="Q")
        self.play(weak, strong, 5, 3)
        upset_gain = weak[0].score - 900
        weak, strong = self.players(900, 900, prefix="R"), self.players(1100, 1100, prefix="S")
        self.play(strong, weak, 5, 3)
        expected_gain = strong[0].score - 1100
        self.assertGreater(upset_gain, expected_gain)
        self.assertGreater(expected_gain, 0)

    def test_new_players_change_faster(self):
        regular, new = self.players(1000, 1000)
        regular.sigma = 2.0
        regular.save()
        opponents = self.players(1000, 1000, prefix="Q")
        self.play([regular, new], opponents, 5, 3)
        self.assertGreater(new.score - 1000, regular.score - 1000)
        self.assertGreater(regular.score, 1000)

    def test_uneven_teams(self):
        a = self.players(1000, 1000, 1000)
        b = self.players(1000, 1000, prefix="Q")
        self.play(a, b, 3, 7)
        self.assertTrue(all(p.score < 1000 for p in a))
        self.assertTrue(all(p.score > 1000 for p in b))

    def test_player_never_rated_starts_from_current_score(self):
        """Players created before the ratings existed have no mu/sigma."""
        legacy = make_player(self.user, "Legacy", score=1400)
        self.assertIsNone(legacy.mu)
        a = [legacy] + self.players(1000)
        b = self.players(1200, 1200, prefix="Q")
        self.play(a, b, 3, 5)
        self.assertLess(legacy.score, 1400)
        self.assertGreater(legacy.score, 1300)
        self.assertIsNotNone(legacy.mu)

    def test_issue_8_more_wins_rank_higher(self):
        """A player who won 12 games and lost 2 should be ranked higher than
        a player who only won 3 games. As in real games, the teams change
        from one game to another (with always the same teammates, the
        system cannot know who made the team win)."""
        x, y = self.players(1000, 1000, prefix="Star")
        others = self.players(*([1000] * 12), prefix="O")
        rng = random.Random(0)

        def play(star, won):
            team = rng.sample(others, 9)
            score_a, score_b = (5, 3) if won else (3, 5)
            self.play([star] + team[:4], team[4:], score_a, score_b)

        for i in range(3):
            play(x, True)
        results = [True] * 12 + [False] * 2
        rng.shuffle(results)
        for won in results:
            play(y, won)
        self.assertGreater(y.score, x.score)

    def test_win_loss_draw_stats_and_points(self):
        a = self.players(1000, 1000)
        b = self.players(1000, 1000, prefix="Q")
        self.play(a, b, 5, 3)
        self.play(a, b, 2, 2)
        self.play(a, b, 1, 4)
        for p in a + b:
            s = self.stats(p)
            self.assertEqual((s.win, s.draw, s.loss), (1, 1, 1))
            self.assertEqual(s.total_points, 4)  # 3 for the win, 1 for the draw

    def test_league_points(self):
        a = self.players(1000)
        b = self.players(1000, prefix="Q")
        self.play(a, b, 5, 3)
        self.play(a, b, 5, 3)
        self.assertEqual(self.stats(a[0]).total_points, 6)
        self.assertEqual(self.stats(b[0]).total_points, 0)

    def test_stats_are_per_league(self):
        a = self.players(1000)
        b = self.players(1000, prefix="Q")
        self.play(a, b, 5, 3)
        other = make_league(self.user, "Other")
        self.play(a, b, 0, 1, league=other)
        self.assertEqual(self.stats(a[0]).win, 1)
        self.assertEqual(self.stats(a[0], other).loss, 1)


class LeagueScoreTests(RatingTestCase):
    def test_new_league_starts_from_the_initial_score(self):
        a = self.players(1300, 1000)
        b = self.players(1000, 1000, prefix="Q")
        self.play(a, b, 5, 3)
        other = make_league(self.user, "Other")
        a[0].score = 2000  # the global score does not matter for a new league
        a[0].save()
        self.play(a, b, 4, 4, league=other)
        self.assertLess(abs(self.stats(a[0], other).score - 1300), 100)

    def test_league_score_only_counts_the_games_of_the_league(self):
        a = self.players(1000, 1000)
        b = self.players(1000, 1000, prefix="Q")
        other = make_league(self.user, "Other")
        for i in range(3):
            self.play(a, b, 5, 3)                 # a wins in this league
        self.play(a, b, 3, 5, league=other)      # ... and loses in the other one
        self.assertGreater(a[0].score, 1000)                    # global: 3 wins, 1 loss
        self.assertGreater(self.stats(a[0]).score, 1000)        # this league: 3 wins
        self.assertLess(self.stats(a[0], other).score, 1000)    # other league: 1 loss

    def test_league_score_after_a_single_league_is_the_global_score(self):
        a = self.players(1000, 1100)
        b = self.players(950, 1050, prefix="Q")
        self.play(a, b, 5, 3)
        self.play(b, a, 5, 3)
        for p in a + b:
            stats = self.stats(p)
            self.assertEqual(stats.score, p.score)
            self.assertAlmostEqual(stats.mu, p.mu)


class RecomputeTests(RatingTestCase):
    def test_recompute_replays_the_history(self):
        a = self.players(1000, 1100)
        b = self.players(950, 1050, prefix="Q")
        self.play(a, b, 5, 3)
        self.play(b, a, 5, 3)
        self.play(a, b, 4, 4)
        self.play(a, b, 2, 7, league=make_league(self.user, "Other"))
        expected = {p.pk: (p.score, p.mu, p.sigma) for p in Player.objects.all()}
        expected_stats = [(s.player_id, s.league_id, s.win, s.loss, s.draw, s.total_points, s.score)
                          for s in PlayerStats.objects.all()]

        # break everything, then recompute
        Player.objects.update(score=0, mu=None, sigma=None)
        PlayerStats.objects.update(win=9, total_points=99, score=0, mu=None)
        rating.recompute_all()

        for p in Player.objects.all():
            score, mu, sigma = expected[p.pk]
            self.assertEqual(p.score, score)
            self.assertAlmostEqual(p.mu, mu)
            self.assertAlmostEqual(p.sigma, sigma)
        self.assertCountEqual([(s.player_id, s.league_id, s.win, s.loss, s.draw, s.total_points, s.score)
                               for s in PlayerStats.objects.all()], expected_stats)

    def test_recompute_starts_from_the_initial_score(self):
        p = make_player(self.user, "Old", score=2345)
        p.initial_score = 1300
        p.save()
        rating.recompute_all()
        p.refresh_from_db()
        self.assertEqual(p.score, 1300)

    def test_recompute_follows_the_completion_order(self):
        a = self.players(1000)
        b = self.players(1000, prefix="Q")
        first = self.play(a, b, 5, 3)
        second = self.play(a, b, 3, 5)
        after_games = (a[0].score, b[0].score)
        # same games, completed in the other order: the result differs
        first.completion_date, second.completion_date = second.completion_date, first.completion_date
        first.save()
        second.save()
        rating.recompute_all()
        a[0].refresh_from_db()
        b[0].refresh_from_db()
        self.assertNotEqual((a[0].score, b[0].score), after_games)

    def test_ongoing_games_are_ignored(self):
        a = self.players(1000)
        b = self.players(1000, prefix="Q")
        make_game(self.league, a, b)
        rating.recompute_all()
        a[0].refresh_from_db()
        self.assertEqual(a[0].score, 1000)
        self.assertFalse(PlayerStats.objects.exists())

    def test_command_dry_run(self):
        a = self.players(1000)
        b = self.players(1000, prefix="Q")
        self.play(a, b, 5, 3)
        Player.objects.update(score=0)
        out = StringIO()
        call_command("recompute_ratings", "--dry-run", stdout=out)
        self.assertIn("Dry run", out.getvalue())
        self.assertIn(a[0].name, out.getvalue())
        self.assertEqual(Player.objects.get(pk=a[0].pk).score, 0)

    def test_command(self):
        a = self.players(1000)
        b = self.players(1000, prefix="Q")
        self.play(a, b, 5, 3)
        winner_score = a[0].score
        Player.objects.update(score=0)
        out = StringIO()
        call_command("recompute_ratings", stdout=out)
        self.assertIn("Recomputed the ratings of 2 players", out.getvalue())
        self.assertEqual(Player.objects.get(pk=a[0].pk).score, winner_score)
