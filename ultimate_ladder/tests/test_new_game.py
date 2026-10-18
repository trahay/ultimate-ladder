"""End-to-end tests of the team generation (NewGame view)."""
import random

from django.test import TestCase
from django.urls import reverse

from ultimate_ladder.models import Game, Team

from .utils import PASSWORD, make_game, make_league, make_player, make_user, seed


class NewGameTests(TestCase):
    def setUp(self):
        seed(0)
        random.seed(0)
        self.user = make_user("alice")
        self.league = make_league(self.user)
        self.client.login(username="alice", password=PASSWORD)

    def url(self, league=None, owner="alice"):
        league = league or self.league
        return reverse("add-game", kwargs={"owner": owner, "league_pk": league.pk})

    def create_game(self, players):
        response = self.client.post(self.url(), {"players": [p.pk for p in players]})
        game = Game.objects.latest("pk")
        self.assertRedirects(response, reverse(
            "game", kwargs={"owner": "alice", "league_id": self.league.pk, "pk": game.pk}))
        team_a = [t.player for t in game.team_set.filter(team_name="A")]
        team_b = [t.player for t in game.team_set.filter(team_name="B")]
        return game, team_a, team_b

    def roster(self, nb_men, nb_women, scores=None):
        scores = scores or [random.randint(500, 1500) for _ in range(nb_men + nb_women)]
        genders = ["m"] * nb_men + ["f"] * nb_women
        return [make_player(self.user, f"P{i}", g, s)
                for i, (g, s) in enumerate(zip(genders, scores))]

    def assertBalanced(self, players, team_a, team_b):
        self.assertCountEqual(team_a + team_b, players)
        self.assertLessEqual(abs(len(team_a) - len(team_b)), 1)
        women_a = sum(p.gender == "f" for p in team_a)
        women_b = sum(p.gender == "f" for p in team_b)
        self.assertLessEqual(abs(women_a - women_b), 1)

    # --- Form / access -------------------------------------------------

    def test_get_lists_only_the_owner_players(self):
        mine = make_player(self.user, "Mine")
        other = make_player(make_user("bob"), "NotMine")
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, mine.name)
        self.assertNotContains(response, other.name)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_at_least_two_players(self):
        p = make_player(self.user, "Alone")
        response = self.client.post(self.url(), {"players": [p.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select at least two players.")
        self.assertFalse(Game.objects.exists())

    def test_unknown_league(self):
        response = self.client.get(reverse("add-game", kwargs={"owner": "alice", "league_pk": 999}))
        self.assertEqual(response.status_code, 404)

    def test_cannot_use_players_of_another_user(self):
        other = make_player(make_user("bob"), "NotMine")
        mine = make_player(self.user, "Mine")
        response = self.client.post(self.url(), {"players": [mine.pk, other.pk]})
        self.assertEqual(response.status_code, 200)  # form error
        self.assertFalse(Game.objects.exists())

    def test_cannot_create_game_in_another_user_league(self):
        bob = make_user("bob")
        bob_league = make_league(bob)
        players = [make_player(bob, "B1"), make_player(bob, "B2")]
        response = self.client.post(self.url(bob_league, owner="bob"),
                                    {"players": [p.pk for p in players]})
        self.assertEqual(response.status_code, 404)

    # --- Player list (issue #2) ----------------------------------------

    def preselected(self, league=None):
        """Ids of the players that are checked in the new game form."""
        response = self.client.get(self.url(league))
        self.assertEqual(response.status_code, 200)
        return {int(pk) for pk in response.context["form"]["players"].value()}

    def test_players_are_sorted_by_name(self):
        for name in ["charlie", "Bob", "alice", "Dave"]:
            make_player(self.user, name)
        response = self.client.get(self.url())
        names = [p.name for p in response.context["form"].fields["players"].queryset]
        self.assertEqual(names, ["alice", "Bob", "charlie", "Dave"])
        content = response.content.decode()
        positions = [content.index(n) for n in names]
        self.assertEqual(positions, sorted(positions))

    def test_nothing_preselected_without_previous_game(self):
        make_player(self.user, "P1")
        self.assertEqual(self.preselected(), set())

    def test_players_of_last_game_are_preselected(self):
        players = self.roster(3, 2)
        absent = make_player(self.user, "Absent")
        game, team_a, team_b = self.create_game(players)
        self.assertEqual(self.preselected(), {p.pk for p in players})
        response = self.client.get(self.url())
        self.assertContains(response, 'checked', count=len(players))
        self.assertNotIn(absent.pk, self.preselected())

    def test_only_the_last_game_is_used(self):
        p = self.roster(4, 0)
        make_game(self.league, [p[0]], [p[1]])
        make_game(self.league, [p[2]], [p[3]])
        self.assertEqual(self.preselected(), {p[2].pk, p[3].pk})

    def test_last_game_of_the_league_has_priority(self):
        p = self.roster(4, 0)
        other_league = make_league(self.user, "Other")
        make_game(self.league, [p[0]], [p[1]])
        make_game(other_league, [p[2]], [p[3]])  # more recent, other league
        self.assertEqual(self.preselected(), {p[0].pk, p[1].pk})

    def test_new_league_uses_last_game_of_the_owner(self):
        p = self.roster(2, 0)
        make_game(self.league, [p[0]], [p[1]])
        new_league = make_league(self.user, "New")
        self.assertEqual(self.preselected(new_league), {p[0].pk, p[1].pk})

    def test_games_of_other_users_are_ignored(self):
        bob = make_user("bob")
        bob_players = [make_player(bob, "B1"), make_player(bob, "B2")]
        make_game(make_league(bob), [bob_players[0]], [bob_players[1]])
        make_player(self.user, "P1")
        self.assertEqual(self.preselected(), set())

    # --- Team generation ---------------------------------------------

    def test_game_and_teams_are_created(self):
        players = self.roster(2, 2, [1000, 1100, 900, 950])
        game, team_a, team_b = self.create_game(players)
        self.assertFalse(game.completed)
        self.assertEqual(game.owner, self.user)
        self.assertEqual(game.league, self.league)
        self.assertEqual(Team.objects.filter(game=game).count(), 4)
        for t in Team.objects.filter(game=game):
            self.assertEqual(t.player_score, t.player.score)
            self.assertEqual(t.owner, self.user)

    def test_two_players(self):
        players = self.roster(2, 0)
        game, team_a, team_b = self.create_game(players)
        self.assertEqual((len(team_a), len(team_b)), (1, 1))

    def test_one_man_one_woman(self):
        players = self.roster(1, 1)
        game, team_a, team_b = self.create_game(players)
        self.assertEqual((len(team_a), len(team_b)), (1, 1))

    def test_women_are_split_between_teams(self):
        players = self.roster(4, 4)
        game, team_a, team_b = self.create_game(players)
        self.assertEqual(sum(p.gender == "f" for p in team_a), 2)
        self.assertEqual(sum(p.gender == "f" for p in team_b), 2)

    def test_odd_men_and_odd_women(self):
        """With an odd number of men and of women, each gender gives the extra
        player to one team; the view must give them to different teams."""
        for nb_men, nb_women in [(3, 3), (5, 1), (1, 3), (5, 3)]:
            with self.subTest(men=nb_men, women=nb_women):
                Team.objects.all().delete()
                players = self.roster(nb_men, nb_women)
                game, team_a, team_b = self.create_game(players)
                self.assertBalanced(players, team_a, team_b)

    def test_many_rosters_are_balanced(self):
        for i in range(10):
            nb_men, nb_women = random.randint(0, 8), random.randint(0, 5)
            if nb_men + nb_women < 2:
                continue
            with self.subTest(men=nb_men, women=nb_women):
                players = self.roster(nb_men, nb_women)
                game, team_a, team_b = self.create_game(players)
                self.assertBalanced(players, team_a, team_b)

    def test_scores_are_balanced_with_even_counts(self):
        """With an even number of men and of women, the total scores of the
        two teams must be close."""
        for i in range(5):
            players = self.roster(6, 4)
            with self.subTest(scores=[p.score for p in players]):
                game, team_a, team_b = self.create_game(players)
                diff = abs(sum(p.score for p in team_a) - sum(p.score for p in team_b))
                average = sum(p.score for p in players) / len(players)
                self.assertLess(diff, 0.5 * average)
