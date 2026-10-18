from django.test import TestCase

from ultimate_ladder.models import PlayerStats, Team

from .utils import make_game, make_league, make_player, make_user


class ModelTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_player_defaults(self):
        p = make_player(self.user, "Bob")
        self.assertEqual(p.score, 1000)
        self.assertEqual(str(p), "Bob (m)")
        self.assertEqual(p.value(), (p.id, "Bob"))

    def test_league_str(self):
        self.assertEqual(str(make_league(self.user, "Sunday")), "Sunday")

    def test_game_defaults(self):
        league = make_league(self.user)
        game = make_game(league, [], [])
        self.assertFalse(game.completed)
        self.assertEqual(game.score_team_a, 0)
        self.assertEqual(game.score_team_b, 0)
        self.assertTrue(str(game).startswith("League ("))

    def test_team_keeps_score_snapshot(self):
        league = make_league(self.user)
        p = make_player(self.user, "Bob", score=1234)
        game = make_game(league, [p], [])
        p.score = 2000
        p.save()
        self.assertEqual(Team.objects.get(game=game).player_score, 1234)

    def test_player_stats_defaults(self):
        league = make_league(self.user)
        p = make_player(self.user, "Bob")
        stats = PlayerStats.objects.create(owner=self.user, player=p, league=league)
        self.assertEqual((stats.win, stats.loss, stats.draw, stats.total_points),
                         (0, 0, 0, 0))

    def test_deleting_user_cascades(self):
        league = make_league(self.user)
        p = make_player(self.user, "Bob")
        make_game(league, [p], [])
        self.user.delete()
        self.assertFalse(Team.objects.exists())
