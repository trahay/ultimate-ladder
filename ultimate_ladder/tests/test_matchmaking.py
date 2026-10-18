"""Tests of create_team(), which splits a group of players (of one gender)
in two teams with a similar total score."""
import random
import unittest

import pandas as pd
from django.test import SimpleTestCase

from ultimate_ladder.views import create_team

from .utils import best_split_difference, seed


def run(skills):
    df = pd.DataFrame({"player": list(range(len(skills))), "skill": skills})
    return create_team(df)


def team_sum(team, skills):
    return sum(skills[i] for i in team)


class CreateTeamTests(SimpleTestCase):
    def setUp(self):
        seed(0)
        random.seed(0)

    def test_no_player(self):
        self.assertEqual(run([]), ([], []))

    def test_single_player_goes_to_team_a(self):
        self.assertEqual(run([1000]), ([0], []))

    def test_two_players(self):
        a, b = run([800, 1200])
        self.assertEqual(sorted(a + b), [0, 1])
        self.assertEqual((len(a), len(b)), (1, 1))

    def test_every_player_is_assigned_exactly_once(self):
        for n in range(2, 11):
            with self.subTest(n=n):
                skills = [random.randint(500, 1500) for _ in range(n)]
                a, b = run(skills)
                self.assertEqual(sorted(a + b), list(range(n)))

    def test_team_sizes_differ_by_at_most_one(self):
        for n in range(2, 11):
            with self.subTest(n=n):
                skills = [random.randint(500, 1500) for _ in range(n)]
                a, b = run(skills)
                self.assertLessEqual(abs(len(a) - len(b)), 1)

    def test_identical_scores(self):
        a, b = run([1000] * 6)
        self.assertEqual((len(a), len(b)), (3, 3))

    def test_obvious_split(self):
        # The only balanced split is {2000, 0} vs {1000, 1000}
        skills = [2000, 1000, 1000, 1]
        a, b = run(skills)
        self.assertLessEqual(abs(team_sum(a, skills) - team_sum(b, skills)), 1)

    def test_even_number_of_players_is_balanced(self):
        """The heuristic should be close to the optimal split: at most a
        quarter of an average player's score worse."""
        for i in range(15):
            n = random.choice([4, 6, 8])
            skills = [random.randint(500, 1500) for _ in range(n)]
            with self.subTest(skills=skills):
                a, b = run(skills)
                diff = abs(team_sum(a, skills) - team_sum(b, skills))
                tolerance = 0.25 * sum(skills) / n
                self.assertLessEqual(diff, best_split_difference(skills) + tolerance)

    @unittest.expectedFailure
    def test_odd_number_of_players_is_balanced(self):
        """KNOWN ISSUE: the matchmaking library balances the *average* score
        of the teams, not their sum. With an odd number of players, the team
        with one more player ends up much stronger: here it builds
        {500, 1500} vs {1000} (same average, sums 2000 vs 1000) instead of
        {500, 1000} vs {1500}."""
        skills = [500, 1000, 1500]
        a, b = run(skills)
        self.assertLessEqual(abs(team_sum(a, skills) - team_sum(b, skills)), 250)
