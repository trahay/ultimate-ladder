"""Tests of the content of the pages (leagues, players, standings...)."""
import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ultimate_ladder.models import PlayerStats
from ultimate_ladder.views import UpdateStats, leagues_with_stats, players_by_name, recent_games

from .utils import PASSWORD, make_game, make_league, make_player, make_user


def finish(game, score_a, score_b, update_stats=True):
    game.score_team_a, game.score_team_b, game.completed = score_a, score_b, True
    game.save()
    if update_stats:
        UpdateStats(game)
    return game


class PageTestCase(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        self.league = make_league(self.user, "Sunday league")


class LeaguePageTests(PageTestCase):
    def url(self):
        return reverse("league", kwargs={"owner": "alice", "pk": self.league.pk})

    def test_empty_league(self):
        response = self.client.get(self.url())
        self.assertNotContains(response, "Ongoing games")
        self.assertContains(response, "The standings will appear once a game is completed.")
        self.assertContains(response, "No completed game yet.")

    def test_no_ongoing_section_when_all_games_are_completed(self):
        a, b = make_player(self.user, "A1"), make_player(self.user, "B1")
        finish(make_game(self.league, [a], [b]), 5, 3)
        response = self.client.get(self.url())
        self.assertNotContains(response, "Ongoing games")
        self.assertContains(response, "A 5 – 3 B")
        self.assertContains(response, "Team A wins")

    def test_ongoing_games(self):
        players = [make_player(self.user, f"P{i}") for i in range(4)]
        make_game(self.league, players[:2], players[2:])
        response = self.client.get(self.url())
        self.assertContains(response, "Ongoing games")
        self.assertContains(response, "4 players")

    def test_standings_are_sorted_by_league_points(self):
        p = {name: make_player(self.user, name) for name in ["Low", "High", "Mid"]}
        for name, points in [("Low", -10), ("High", 50), ("Mid", 5)]:
            PlayerStats.objects.create(owner=self.user, player=p[name], league=self.league,
                                       total_points=points)
        response = self.client.get(self.url())
        names = [s.player.name for s in response.context["player_list"]]
        self.assertEqual(names, ["High", "Mid", "Low"])

    def test_games_are_listed_most_recent_first(self):
        a, b = make_player(self.user, "A1"), make_player(self.user, "B1")
        old = finish(make_game(self.league, [a], [b]), 1, 0, update_stats=False)
        old.creation_date = timezone.now() - datetime.timedelta(days=7)
        old.save()
        new = finish(make_game(self.league, [a], [b]), 0, 1, update_stats=False)
        response = self.client.get(self.url())
        self.assertEqual(list(response.context["completed_games"]), [new, old])

    def test_actions_are_hidden_to_anonymous_users(self):
        self.client.logout()
        response = self.client.get(self.url())
        self.assertNotContains(response, "New game")
        self.assertNotContains(response, "Delete league")


class LeagueListTests(PageTestCase):
    def test_leagues_with_stats(self):
        other = make_league(self.user, "Empty league")
        players = [make_player(self.user, f"P{i}") for i in range(4)]
        finish(make_game(self.league, players[:2], players[2:]), 3, 2)
        make_game(self.league, players[:1], players[1:2])
        leagues = list(leagues_with_stats(self.user))
        # the league with games comes first, the empty one last
        self.assertEqual(leagues, [self.league, other])
        self.assertEqual((leagues[0].nb_games, leagues[0].nb_players), (2, 4))
        self.assertIsNotNone(leagues[0].last_game)
        self.assertEqual((leagues[1].nb_games, leagues[1].nb_players, leagues[1].last_game), (0, 0, None))

    def test_leagues_page(self):
        make_league(self.user, "Empty league")
        response = self.client.get(reverse("leagues", kwargs={"owner": "alice"}))
        self.assertContains(response, "Sunday league")
        self.assertContains(response, "0 games · 0 players")
        self.assertContains(response, "No game yet")
        self.assertContains(response, "Create league")

    def test_no_league(self):
        self.league.delete()
        response = self.client.get(reverse("leagues", kwargs={"owner": "alice"}))
        self.assertContains(response, "No league yet.")

    def test_home_page(self):
        make_player(self.user, "Zoe", "f")
        make_player(self.user, "bob")
        response = self.client.get(reverse("index", kwargs={"owner": "alice"}))
        self.assertContains(response, "Sunday league")
        self.assertEqual([p.name for p in response.context["all_players"]], ["bob", "Zoe"])
        self.assertContains(response, 'aria-label="woman"', count=1)


class PlayerListTests(PageTestCase):
    def test_players_are_sorted_by_name(self):
        for name in ["charlie", "Bob", "alice"]:
            make_player(self.user, name)
        response = self.client.get(reverse("players", kwargs={"owner": "alice"}))
        self.assertEqual([p.name for p in response.context["player_list"]], ["alice", "Bob", "charlie"])
        self.assertContains(response, "Create player")

    def test_no_player(self):
        response = self.client.get(reverse("players", kwargs={"owner": "alice"}))
        self.assertContains(response, "No player yet.")

    def test_game_stats_of_players(self):
        me, other = make_player(self.user, "Me"), make_player(self.user, "Other")
        second = make_league(self.user, "Second league")
        finish(make_game(self.league, [me], [other]), 5, 3)   # win
        finish(make_game(self.league, [me], [other]), 2, 2)   # draw
        finish(make_game(second, [other], [me]), 4, 1)        # loss, other league
        finish(make_game(second, [me], [other]), 3, 0)        # win
        make_game(second, [me], [other])                      # ongoing: not counted
        stats = {p.name: p for p in players_by_name(self.user)}
        self.assertEqual((stats["Me"].played, stats["Me"].wins, stats["Me"].losses, stats["Me"].draws),
                         (4, 2, 1, 1))
        self.assertEqual(stats["Me"].win_rate, 50)
        self.assertEqual(stats["Other"].win_rate, 25)

    def test_player_without_game_has_no_win_rate(self):
        make_player(self.user, "New")
        player = players_by_name(self.user).get()
        self.assertEqual((player.played, player.wins), (0, 0))
        self.assertIsNone(player.win_rate)
        response = self.client.get(reverse("players", kwargs={"owner": "alice"}))
        self.assertContains(response, '<td data-order="-1">–</td>', html=True)

    def test_detailed_columns_only_on_players_page(self):
        make_player(self.user, "Bob")
        players_page = self.client.get(reverse("players", kwargs={"owner": "alice"}))
        home_page = self.client.get(reverse("index", kwargs={"owner": "alice"}))
        for column in ["Played", "Win %"]:
            self.assertContains(players_page, f'<span class="label-long">{column}</span>')
            self.assertContains(home_page, f'<span class="label-long">{column}</span>')
        for column in ["Wins", "Losses", "Draws"]:
            self.assertContains(players_page, f'<span class="label-long">{column}</span>')
            self.assertNotContains(home_page, f'<span class="label-long">{column}</span>')


class PlayerPageTests(PageTestCase):
    def setUp(self):
        super().setUp()
        self.me = make_player(self.user, "Me", "f")
        self.other = make_player(self.user, "Other")

    def test_recent_games_results(self):
        finish(make_game(self.league, [self.me], [self.other]), 5, 3)    # A: win
        finish(make_game(self.league, [self.other], [self.me]), 5, 3)    # B: loss
        finish(make_game(self.league, [self.other], [self.me]), 2, 2)    # B: draw
        make_game(self.league, [self.other], [self.me])                  # ongoing
        games = recent_games(self.me)
        self.assertEqual([(g["team_name"], g["result"]) for g in games],
                         [("B", None), ("B", "draw"), ("B", "loss"), ("A", "win")])
        # the score is given from the point of view of the player
        self.assertEqual((games[2]["own"], games[2]["other"]), (3, 5))

    def test_recent_games_are_limited(self):
        for i in range(12):
            make_game(self.league, [self.me], [self.other])
        self.assertEqual(len(recent_games(self.me)), 10)

    def test_player_page(self):
        finish(make_game(self.league, [self.me], [self.other]), 5, 3)
        finish(make_game(self.league, [self.other], [self.me]), 5, 3)
        response = self.client.get(reverse("player", kwargs={"owner": "alice", "pk": self.me.pk}))
        totals = response.context["totals"]
        self.assertEqual((totals.played, totals.wins, totals.losses, totals.draws), (2, 1, 1, 0))
        self.assertContains(response, '<span class="metric-value">50%</span>', html=True)
        self.assertContains(response, "Sunday league")
        self.assertContains(response, "Last games")
        self.assertContains(response, "Win")
        self.assertContains(response, "Edit player")

    def test_player_without_game(self):
        response = self.client.get(reverse("player", kwargs={"owner": "alice", "pk": self.me.pk}))
        self.assertContains(response, "Me has not completed any game yet.")
        self.assertNotContains(response, "Last games")


class FormPagesTests(PageTestCase):
    def test_new_game_page(self):
        make_player(self.user, "Zoe", "f")
        make_player(self.user, "Bob")
        response = self.client.get(reverse("add-game", kwargs={"owner": "alice", "league_pk": self.league.pk}))
        self.assertContains(response, "Zoe")
        self.assertContains(response, 'id="selection-summary"')
        self.assertContains(response, 'label class="woman"', count=1)

    def test_new_game_page_without_player(self):
        response = self.client.get(reverse("add-game", kwargs={"owner": "alice", "league_pk": self.league.pk}))
        self.assertContains(response, "create the players")

    def test_edit_pages_have_a_cancel_button(self):
        player = make_player(self.user, "Bob")
        for url, cancel in [
                (reverse("add-player", kwargs={"owner": "alice"}), reverse("players", kwargs={"owner": "alice"})),
                (reverse("edit-player", kwargs={"owner": "alice", "pk": player.pk}),
                 reverse("player", kwargs={"owner": "alice", "pk": player.pk})),
                (reverse("add-league", kwargs={"owner": "alice"}), reverse("leagues", kwargs={"owner": "alice"})),
                (reverse("edit-league", kwargs={"owner": "alice", "pk": self.league.pk}),
                 reverse("league", kwargs={"owner": "alice", "pk": self.league.pk}))]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, f'<a href="{cancel}" role="button" class="secondary outline">Cancel</a>',
                                    html=True)

    def test_login_page(self):
        self.client.logout()
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Log in")
        response = self.client.post(reverse("login"), {"username": "alice", "password": "wrong"})
        self.assertContains(response, "didn't match")
