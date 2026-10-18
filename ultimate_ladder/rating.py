"""Ratings of the players, computed with OpenSkill
(https://openskill.me), a rating system similar to TrueSkill.

Each player has an estimated skill (mu) and an uncertainty on this
estimation (sigma). After each game, the ratings of the players are
updated depending on the result (win, loss or draw) and on the ratings of
both teams: beating a stronger team gives more points, and the rating of
a new player (high sigma) changes faster than the one of a regular player.
The score difference of the game is not taken into account.

The displayed score is the estimated skill (mu), scaled so that a new
player starts at 1000. It is also used to create balanced teams. (A
conservative estimate such as mu - 3 sigma would make every score increase
after each game, even after a draw, since sigma decreases.)
"""
from django.db import transaction
from openskill.models import PlackettLuce

MODEL = PlackettLuce()

DEFAULT_SCORE = 1000
SCALE = 40


def display_score(mu, sigma):
    return round(DEFAULT_SCORE + SCALE * (mu - MODEL.mu))


def initial_rating(score):
    """(mu, sigma) of a new player whose displayed score is `score`."""
    return MODEL.mu + (score - DEFAULT_SCORE) / SCALE, MODEL.sigma


def reset_player(player):
    """Set the rating of a player from their initial score (not saved)."""
    player.mu, player.sigma = initial_rating(player.initial_score)
    player.score = display_score(player.mu, player.sigma)


def current_rating(player):
    """(mu, sigma) of a player. Players that were never rated (e.g. created
    before the ratings existed) start from their current score."""
    if player.mu is None or player.sigma is None:
        return initial_rating(player.score)
    return player.mu, player.sigma


def game_result(game):
    """'A', 'B' or 'draw'."""
    if game.score_team_a > game.score_team_b:
        return 'A'
    if game.score_team_b > game.score_team_a:
        return 'B'
    return 'draw'


def rate_game(game, players=None):
    """Update the ratings of the players of a completed game.

    `players` maps player ids to Player objects: when given, these objects
    are updated (and not saved), so that a sequence of games can be rated
    in memory. Otherwise, the players are loaded and saved.
    """
    teams = {'A': [], 'B': []}
    for t in game.team_set.select_related('player').order_by('id'):
        player = players[t.player_id] if players is not None else t.player
        teams[t.team_name].append(player)
    if not teams['A'] or not teams['B']:
        return

    result = game_result(game)
    ranks = {'A': [1, 2], 'B': [2, 1], 'draw': [1, 1]}[result]
    model_teams = [[MODEL.rating(*current_rating(p)) for p in teams[name]] for name in ('A', 'B')]
    new_teams = MODEL.rate(model_teams, ranks=ranks)

    for name, new_team in zip(('A', 'B'), new_teams):
        for player, rating in zip(teams[name], new_team):
            player.mu, player.sigma = rating.mu, rating.sigma
            player.score = display_score(rating.mu, rating.sigma)
            if players is None:
                player.save(update_fields=['mu', 'sigma', 'score'])


def league_points(won, drawn):
    """Points in the standings of a league: 3 per win, 1 per draw."""
    return 3 if won else 1 if drawn else 0


def update_stats(game, player, team_name):
    """Update the statistics (win/loss/draw, points) of a player in the
    league of a completed game."""
    from .models import PlayerStats
    stats, created = PlayerStats.objects.get_or_create(player=player, league=game.league, owner=game.owner)
    result = game_result(game)
    if result == 'draw':
        stats.draw += 1
    elif result == team_name:
        stats.win += 1
    else:
        stats.loss += 1
    stats.total_points += league_points(result == team_name, result == 'draw')
    stats.save()


def complete_game(game):
    """Update the ratings and statistics of the players of a game that was
    just completed."""
    with transaction.atomic():
        rate_game(game)
        for t in game.team_set.select_related('player'):
            update_stats(game, t.player, t.team_name)


def recompute_all():
    """Recompute the ratings and statistics of all the players, by
    replaying all the completed games in the order they were completed.

    Returns the list of (player, old score, new score)."""
    from .models import Game, Player, PlayerStats
    with transaction.atomic():
        players = {p.id: p for p in Player.objects.select_related('owner')}
        old_scores = {pid: p.score for pid, p in players.items()}
        for player in players.values():
            reset_player(player)
        PlayerStats.objects.all().delete()

        games = Game.objects.filter(completed=True).order_by('completion_date', 'creation_date', 'id')
        for game in games:
            rate_game(game, players)
            for t in game.team_set.all():
                update_stats(game, players[t.player_id], t.team_name)

        Player.objects.bulk_update(players.values(), ['mu', 'sigma', 'score'])
        return [(p, old_scores[pid], p.score) for pid, p in players.items()]
