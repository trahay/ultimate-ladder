import itertools

import numpy as np
from django.contrib.auth import get_user_model
from django.utils import timezone

from ultimate_ladder.models import Game, League, Player, Team

User = get_user_model()

PASSWORD = "test-password"


def make_user(username="alice"):
    return User.objects.create_user(username=username, password=PASSWORD)


def make_player(owner, name, gender="m", score=1000):
    return Player.objects.create(owner=owner, name=name, gender=gender, score=score)


def make_league(owner, name="League"):
    return League.objects.create(owner=owner, name=name)


def make_game(league, team_a, team_b):
    """Create a game with the given players (lists of Player) in each team."""
    game = Game.objects.create(owner=league.owner, league=league,
                               creation_date=timezone.now())
    for team_name, players in (("A", team_a), ("B", team_b)):
        for p in players:
            Team.objects.create(owner=league.owner, game=game, player=p,
                                player_score=p.score, team_name=team_name)
    return game


def best_split_difference(skills):
    """Smallest possible |sum(A) - sum(B)| when splitting `skills` in two
    teams whose sizes differ by at most one (brute force)."""
    total = sum(skills)
    n = len(skills)
    return min(abs(2 * sum(skills[i] for i in combo) - total)
               for combo in itertools.combinations(range(n), n // 2))


def seed(value=0):
    """The matchmaking algorithm relies on numpy's random generator."""
    np.random.seed(value)
