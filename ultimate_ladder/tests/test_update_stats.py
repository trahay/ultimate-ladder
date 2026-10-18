"""Tests of UpdateStats(), which updates the player scores and statistics
once the result of a game is known."""
from django.test import TestCase

from ultimate_ladder.models import Player, PlayerStats
from ultimate_ladder.views import TeamScore, UpdateStats

from .utils import make_game, make_league, make_player, make_user


class UpdateStatsTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.league = make_league(self.user)

    def players(self, *scores):
        return [make_player(self.user, f"P{i}-{s}", score=s) for i, s in enumerate(scores)]

    def play(self, team_a, team_b, score_a, score_b):
        game = make_game(self.league, team_a, team_b)
        game.score_team_a = score_a
        game.score_team_b = score_b
        game.completed = True
        game.save()
        UpdateStats(game)
        return game

    def score(self, player):
        return Player.objects.get(pk=player.pk).score

    def stats(self, player):
        return PlayerStats.objects.get(player=player, league=self.league)

    def test_team_score(self):
        a = self.players(1000, 1200)
        game = make_game(self.league, a, [])
        self.assertEqual(TeamScore(game.team_set.filter(team_name="A")), 2200)

    def test_winners_gain_and_losers_lose(self):
        a = self.players(1000, 1000)
        b = self.players(1000, 1000)
        self.play(a, b, 5, 3)
        # delta = 2 points * 5 * 4 players = 40, shared between the 2 players
        for p in a:
            self.assertEqual(self.score(p), 1040)
        for p in b:
            self.assertEqual(self.score(p), 960)

    def test_team_b_wins(self):
        a = self.players(1000, 1000)
        b = self.players(1000, 1000)
        self.play(a, b, 3, 5)
        for p in a:
            self.assertEqual(self.score(p), 960)
        for p in b:
            self.assertEqual(self.score(p), 1040)

    def test_draw_does_not_change_scores(self):
        a = self.players(1100, 900)
        b = self.players(1000, 1000)
        self.play(a, b, 4, 4)
        self.assertEqual([self.score(p) for p in a + b], [1100, 900, 1000, 1000])

    def test_zero_sum_with_uneven_teams(self):
        a = self.players(1000, 1000, 1000)
        b = self.players(1000, 1000)
        self.play(a, b, 7, 6)
        total = sum(self.score(p) for p in a + b)
        # scores are stored as integers: allow the rounding error
        self.assertAlmostEqual(total, 5000, delta=len(a + b))

    def test_score_never_negative(self):
        a = self.players(1000, 1000)
        b = self.players(10, 10)
        self.play(a, b, 15, 0)
        for p in b:
            self.assertEqual(self.score(p), 0)

    def test_win_loss_draw_stats(self):
        a = self.players(1000, 1000)
        b = self.players(1000, 1000)
        self.play(a, b, 5, 3)
        self.play(a, b, 2, 2)
        self.play(a, b, 1, 4)
        for p in a + b:
            s = self.stats(p)
            self.assertEqual((s.win, s.draw, s.loss), (1, 1, 1))

    def test_stats_are_per_league(self):
        a = self.players(1000)
        b = self.players(1000)
        self.play(a, b, 5, 3)
        other = make_league(self.user, "Other")
        game = make_game(other, a, b)
        game.score_team_a, game.score_team_b = 0, 1
        game.save()
        UpdateStats(game)
        self.assertEqual(self.stats(a[0]).win, 1)
        self.assertEqual(PlayerStats.objects.get(player=a[0], league=other).loss, 1)

    def test_total_points_even_teams(self):
        a = self.players(1000, 1000)
        b = self.players(1000, 1000)
        self.play(a, b, 5, 3)
        for p in a:
            self.assertEqual(self.stats(p).total_points, 40)
        for p in b:
            self.assertEqual(self.stats(p).total_points, -40)

    def test_total_points_follow_score_with_uneven_teams(self):
        a = self.players(1000, 1000, 1000)
        b = self.players(1000, 1000)
        self.play(a, b, 6, 5)
        for p in a + b:
            # scores are stored as integers: allow the rounding error
            self.assertAlmostEqual(self.stats(p).total_points, self.score(p) - 1000, delta=1)
