"""Tests of the creation of a game whose teams are chosen by the user
(NewManualGame view)."""
from django.test import TestCase
from django.urls import reverse

from ultimate_ladder.forms import ManualGameForm
from ultimate_ladder.models import Game, Team

from .utils import PASSWORD, make_game, make_league, make_player, make_user


def field(player):
    return ManualGameForm.field_name(player.id)


class ManualGameTests(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.league = make_league(self.user)
        self.client.login(username="alice", password=PASSWORD)
        self.p = [make_player(self.user, f"P{i}", "f" if i % 2 else "m", 1000 + 100 * i)
                  for i in range(5)]

    def url(self, league=None, owner="alice"):
        league = league or self.league
        return reverse("add-manual-game", kwargs={"owner": owner, "league_pk": league.pk})

    def post(self, team_a, team_b, league=None, owner="alice"):
        data = {field(p): "A" for p in team_a}
        data.update({field(p): "B" for p in team_b})
        return self.client.post(self.url(league, owner), data)

    def teams(self, game):
        return ({t.player for t in game.team_set.filter(team_name="A")},
                {t.player for t in game.team_set.filter(team_name="B")})

    def initial(self, response):
        """{player: team} pre-filled in the form."""
        form = response.context["form"]
        return {p: form[field(p)].value() for p in form.players if form[field(p)].value()}

    # --- Form / access -------------------------------------------------

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_get_lists_only_the_owner_players_sorted_by_name(self):
        make_player(self.user, "aaron")
        make_player(make_user("bob"), "NotMine")
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        names = [p.name for p in response.context["form"].players]
        self.assertEqual(names, ["aaron", "P0", "P1", "P2", "P3", "P4"])
        self.assertNotContains(response, "NotMine")

    def test_unknown_league(self):
        response = self.client.get(reverse("add-manual-game", kwargs={"owner": "alice", "league_pk": 999}))
        self.assertEqual(response.status_code, 404)

    def test_cannot_create_game_in_another_user_league(self):
        bob = make_user("bob")
        bob_league = make_league(bob)
        b = [make_player(bob, "B1"), make_player(bob, "B2")]
        self.assertEqual(self.client.get(self.url(bob_league, owner="bob")).status_code, 404)
        response = self.post([b[0]], [b[1]], bob_league, owner="bob")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Game.objects.exists())

    def test_cannot_use_players_of_another_user(self):
        other = make_player(make_user("bob"), "NotMine")
        response = self.post([self.p[0], other], [self.p[1]])
        game = Game.objects.get()
        self.assertEqual(self.teams(game), ({self.p[0]}, {self.p[1]}))

    def test_links_between_automatic_and_manual_modes(self):
        self.assertContains(self.client.get(self.url()),
                            reverse("add-game", kwargs={"owner": "alice", "league_pk": self.league.pk}))
        self.assertContains(self.client.get(reverse("add-game", kwargs={"owner": "alice", "league_pk": self.league.pk})),
                            self.url())
        self.assertContains(self.client.get(reverse("league", kwargs={"owner": "alice", "pk": self.league.pk})),
                            self.url())

    # --- Validation ----------------------------------------------------

    def test_each_team_needs_a_player(self):
        for team_a, team_b in [([], []), (self.p[:2], []), ([], self.p[:2])]:
            with self.subTest(team_a=team_a, team_b=team_b):
                response = self.post(team_a, team_b)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Each team needs at least one player.")
        self.assertFalse(Game.objects.exists())

    def test_invalid_choice(self):
        response = self.client.post(self.url(), {field(self.p[0]): "A", field(self.p[1]): "C"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Game.objects.exists())

    def test_form_is_kept_on_error(self):
        response = self.post(self.p[:2], [])
        self.assertEqual(self.initial(response), {self.p[0]: "A", self.p[1]: "A"})

    # --- Game creation -------------------------------------------------

    def test_game_and_teams_are_created(self):
        response = self.post([self.p[0], self.p[3]], [self.p[1], self.p[2]])
        game = Game.objects.get()
        self.assertRedirects(response, reverse(
            "game", kwargs={"owner": "alice", "league_id": self.league.pk, "pk": game.pk}))
        self.assertFalse(game.completed)
        self.assertEqual((game.owner, game.league), (self.user, self.league))
        self.assertEqual(self.teams(game), ({self.p[0], self.p[3]}, {self.p[1], self.p[2]}))
        # p[4] is absent
        self.assertFalse(Team.objects.filter(player=self.p[4]).exists())
        for t in Team.objects.all():
            self.assertEqual(t.player_score, t.player.score)
            self.assertEqual(t.owner, self.user)

    def test_unbalanced_teams_are_allowed(self):
        self.post(self.p[:4], [self.p[4]])
        self.assertEqual(self.teams(Game.objects.get()), (set(self.p[:4]), {self.p[4]}))

    def test_game_can_be_scored(self):
        self.post([self.p[0]], [self.p[1]])
        game = Game.objects.get()
        self.client.post(reverse("game", kwargs={"owner": "alice", "league_id": self.league.pk, "pk": game.pk}),
                         {"score_team_a": 5, "score_team_b": 3})
        self.p[0].refresh_from_db()
        self.assertGreater(self.p[0].score, 1000)

    # --- Pre-filled teams ----------------------------------------------

    def test_nothing_prefilled_without_previous_game(self):
        self.assertEqual(self.initial(self.client.get(self.url())), {})

    def test_teams_of_last_game_are_prefilled(self):
        make_game(self.league, [self.p[0]], [self.p[1]])
        make_game(self.league, [self.p[2], self.p[3]], [self.p[4]])
        response = self.client.get(self.url())
        self.assertEqual(self.initial(response), {self.p[2]: "A", self.p[3]: "A", self.p[4]: "B"})
        content = response.content.decode()
        self.assertEqual(content.count('" checked>'), len(self.p))  # 3 in a team + 2 absent
        self.assertIn(f'name="{field(self.p[4])}" value="B" id="id_{field(self.p[4])}_2" checked>', content)

    def test_new_league_uses_last_game_of_the_owner(self):
        make_game(self.league, [self.p[0]], [self.p[1]])
        new_league = make_league(self.user, "New")
        self.assertEqual(self.initial(self.client.get(self.url(new_league))),
                         {self.p[0]: "A", self.p[1]: "B"})
