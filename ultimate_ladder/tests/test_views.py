from django.test import TestCase
from django.urls import reverse

from ultimate_ladder.models import Game, League, Player, PlayerStats

from .utils import PASSWORD, make_game, make_league, make_player, make_user


class ViewTestCase(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.other = make_user("bob")
        self.league = make_league(self.user, "Sunday league")
        self.player = make_player(self.user, "Carol", "f", 1100)

    def login(self, username="alice"):
        self.assertTrue(self.client.login(username=username, password=PASSWORD))


class RedirectTests(ViewTestCase):
    def test_anonymous_goes_to_login(self):
        response = self.client.get("/")
        self.assertRedirects(response, reverse("login"))

    def test_logged_user_goes_to_own_index(self):
        self.login()
        response = self.client.get("/")
        self.assertRedirects(response, reverse("index", kwargs={"owner": "alice"}))


class ReadOnlyPagesTests(ViewTestCase):
    """Pages are public: they can be read without being logged in."""

    def test_index(self):
        url = reverse("index", kwargs={"owner": "alice"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # the content of the index is only displayed to logged users
        self.assertNotContains(response, "Sunday league")
        self.login()
        response = self.client.get(url)
        self.assertContains(response, "Sunday league")
        self.assertContains(response, "Carol")

    def test_players(self):
        make_player(self.other, "NotMine")
        response = self.client.get(reverse("players", kwargs={"owner": "alice"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carol")
        self.assertNotContains(response, "NotMine")

    def test_player(self):
        response = self.client.get(reverse("player", kwargs={"owner": "alice", "pk": self.player.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carol")

    def test_leagues(self):
        make_league(self.other, "Bob league")
        response = self.client.get(reverse("leagues", kwargs={"owner": "alice"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sunday league")
        self.assertNotContains(response, "Bob league")

    def test_league(self):
        response = self.client.get(reverse("league", kwargs={"owner": "alice", "pk": self.league.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sunday league")

    def test_game(self):
        p2 = make_player(self.user, "Dave", "m", 900)
        game = make_game(self.league, [self.player], [p2])
        response = self.client.get(reverse(
            "game", kwargs={"owner": "alice", "league_id": self.league.pk, "pk": game.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["score_team_a"], 1100)
        self.assertEqual(response.context["score_team_b"], 900)
        self.assertContains(response, "Carol")
        self.assertContains(response, "Dave")

    def test_game_team_summaries(self):
        players = [self.player,  # Carol, f, 1100
                   make_player(self.user, "Dave", "m", 900),
                   make_player(self.user, "Erin", "f", 1000),
                   make_player(self.user, "Fred", "m", 800)]
        game = make_game(self.league, players[:2], players[2:])
        response = self.client.get(reverse(
            "game", kwargs={"owner": "alice", "league_id": self.league.pk, "pk": game.pk}))
        team_a, team_b = response.context["teams"]
        self.assertEqual((team_a["name"], team_a["score"], team_a["nb_players"], team_a["nb_women"]),
                         ("A", 2000, 2, 1))
        self.assertEqual((team_b["name"], team_b["score"], team_b["nb_players"], team_b["nb_women"]),
                         ("B", 1800, 2, 1))
        # players are sorted by decreasing score
        self.assertEqual([t.player.name for t in team_a["members"]], ["Carol", "Dave"])
        self.assertEqual(response.context["score_gap"], 200)
        self.assertEqual(response.context["stronger_team"], "A")
        self.assertContains(response, "200 points in favour of team A")
        self.assertContains(response, "2000 points · 2 players · 1 woman")

    def test_ongoing_game_shows_score_form_to_logged_users(self):
        p2 = make_player(self.user, "Dave", "m", 1100)
        game = make_game(self.league, [self.player], [p2])
        url = reverse("game", kwargs={"owner": "alice", "league_id": self.league.pk, "pk": game.pk})
        response = self.client.get(url)
        self.assertContains(response, "Ongoing")
        self.assertNotContains(response, "Save the score")
        self.assertContains(response, "Both teams have the same level")
        self.login()
        response = self.client.get(url)
        self.assertContains(response, "Save the score")
        self.assertContains(response, 'data-target="id_score_team_a"', count=2)
        self.assertContains(response, 'data-target="id_score_team_b"', count=2)

    def test_completed_game_shows_final_score(self):
        p2 = make_player(self.user, "Dave", "m", 900)
        game = make_game(self.league, [self.player], [p2])
        game.score_team_a, game.score_team_b, game.completed = 4, 7, True
        game.save()
        self.login()
        response = self.client.get(reverse(
            "game", kwargs={"owner": "alice", "league_id": self.league.pk, "pk": game.pk}))
        self.assertContains(response, "Completed")
        self.assertContains(response, "Team B wins")
        self.assertContains(response, '<span class="final-score">7</span>', html=False)
        self.assertNotContains(response, "Save the score")

    def test_unknown_player(self):
        response = self.client.get(reverse("player", kwargs={"owner": "alice", "pk": 999}))
        self.assertEqual(response.status_code, 404)


class PlayerEditionTests(ViewTestCase):
    def test_create_requires_login(self):
        response = self.client.get(reverse("add-player", kwargs={"owner": "alice"}))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_create(self):
        self.login()
        response = self.client.post(reverse("add-player", kwargs={"owner": "alice"}),
                                    {"name": "Eve", "gender": "f", "initial_score": 1200})
        self.assertRedirects(response, reverse("players", kwargs={"owner": "alice"}))
        eve = Player.objects.get(name="Eve")
        self.assertEqual((eve.owner, eve.gender, eve.initial_score, eve.score), (self.user, "f", 1200, 1200))
        self.assertIsNotNone(eve.mu)

    def test_create_invalid_gender(self):
        self.login()
        response = self.client.post(reverse("add-player", kwargs={"owner": "alice"}),
                                    {"name": "Eve", "gender": "x", "initial_score": 1200})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Player.objects.filter(name="Eve").exists())

    def test_update(self):
        self.login()
        response = self.client.post(
            reverse("edit-player", kwargs={"owner": "alice", "pk": self.player.pk}),
            {"name": "Caroline", "gender": "f", "initial_score": 1300})
        self.assertRedirects(response, reverse("players", kwargs={"owner": "alice"}))
        self.player.refresh_from_db()
        # no game yet: the score follows the initial score
        self.assertEqual((self.player.name, self.player.initial_score, self.player.score), ("Caroline", 1300, 1300))

    def test_update_initial_score_after_games(self):
        """Once the player has played, changing the initial score does not
        change their current score (it is used when recomputing)."""
        game = make_game(self.league, [self.player], [make_player(self.user, "Dave")])
        game.completed = True
        game.save()
        self.login()
        self.client.post(reverse("edit-player", kwargs={"owner": "alice", "pk": self.player.pk}),
                         {"name": "Carol", "gender": "f", "initial_score": 1500})
        self.player.refresh_from_db()
        self.assertEqual((self.player.initial_score, self.player.score), (1500, 1100))

    def test_delete(self):
        self.login()
        response = self.client.post(
            reverse("delete-player", kwargs={"owner": "alice", "pk": self.player.pk}))
        self.assertRedirects(response, reverse("players", kwargs={"owner": "alice"}))
        self.assertFalse(Player.objects.filter(pk=self.player.pk).exists())

    def test_cannot_update_player_of_another_user(self):
        self.login("bob")
        response = self.client.post(
            reverse("edit-player", kwargs={"owner": "alice", "pk": self.player.pk}),
            {"name": "Hacked", "gender": "f", "initial_score": 0})
        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_player_of_another_user(self):
        self.login("bob")
        response = self.client.post(
            reverse("delete-player", kwargs={"owner": "alice", "pk": self.player.pk}))
        self.assertEqual(response.status_code, 404)


class LeagueEditionTests(ViewTestCase):
    def test_create_requires_login(self):
        response = self.client.post(reverse("add-league", kwargs={"owner": "alice"}), {"name": "X"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(League.objects.filter(name="X").exists())

    def test_create(self):
        self.login()
        response = self.client.post(reverse("add-league", kwargs={"owner": "alice"}), {"name": "Monday"})
        self.assertRedirects(response, reverse("leagues", kwargs={"owner": "alice"}))
        self.assertEqual(League.objects.get(name="Monday").owner, self.user)

    def test_update(self):
        self.login()
        self.client.post(reverse("edit-league", kwargs={"owner": "alice", "pk": self.league.pk}),
                         {"name": "Renamed"})
        self.league.refresh_from_db()
        self.assertEqual(self.league.name, "Renamed")

    def test_delete_cascades_to_games(self):
        self.login()
        make_game(self.league, [self.player], [])
        response = self.client.post(
            reverse("delete-league", kwargs={"owner": "alice", "pk": self.league.pk}))
        self.assertRedirects(response, reverse("leagues", kwargs={"owner": "alice"}))
        self.assertFalse(League.objects.exists())
        self.assertFalse(Game.objects.exists())

    def test_cannot_update_league_of_another_user(self):
        self.login("bob")
        response = self.client.post(
            reverse("edit-league", kwargs={"owner": "alice", "pk": self.league.pk}),
            {"name": "Hacked"})
        self.assertEqual(response.status_code, 404)


class GameResultTests(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.p2 = make_player(self.user, "Dave", "m", 1100)
        self.game = make_game(self.league, [self.player], [self.p2])
        self.url = reverse("game", kwargs={"owner": "alice", "league_id": self.league.pk,
                                           "pk": self.game.pk})

    def test_submit_score(self):
        self.login()
        response = self.client.post(self.url, {"score_team_a": 5, "score_team_b": 3})
        self.assertRedirects(response, reverse("league", kwargs={"owner": "alice", "pk": self.league.pk}))
        self.game.refresh_from_db()
        self.assertTrue(self.game.completed)
        self.assertEqual((self.game.score_team_a, self.game.score_team_b), (5, 3))
        self.assertEqual(PlayerStats.objects.get(player=self.player).win, 1)
        self.assertEqual(PlayerStats.objects.get(player=self.p2).loss, 1)
        self.player.refresh_from_db()
        self.assertGreater(self.player.score, 1100)

    def test_completed_game_cannot_be_scored_twice(self):
        self.login()
        self.client.post(self.url, {"score_team_a": 5, "score_team_b": 3})
        self.player.refresh_from_db()
        score = self.player.score
        response = self.client.post(self.url, {"score_team_a": 0, "score_team_b": 10})
        self.assertRedirects(response, self.url)
        self.game.refresh_from_db()
        self.player.refresh_from_db()
        self.assertEqual((self.game.score_team_a, self.game.score_team_b), (5, 3))
        self.assertEqual(self.player.score, score)
        self.assertEqual(PlayerStats.objects.get(player=self.player).win, 1)

    def test_invalid_score(self):
        self.login()
        response = self.client.post(self.url, {"score_team_a": -1, "score_team_b": 3})
        self.assertRedirects(response, self.url)
        self.game.refresh_from_db()
        self.assertFalse(self.game.completed)

    def test_other_user_cannot_submit_score(self):
        self.login("bob")
        response = self.client.post(self.url, {"score_team_a": 5, "score_team_b": 3})
        self.assertEqual(response.status_code, 404)

    def test_delete_game(self):
        self.login()
        response = self.client.post(reverse(
            "delete-game", kwargs={"owner": "alice", "league_id": self.league.pk, "pk": self.game.pk}))
        self.assertRedirects(response, reverse("leagues", kwargs={"owner": "alice"}))
        self.assertFalse(Game.objects.exists())
        self.assertTrue(Player.objects.filter(pk=self.player.pk).exists())
