"""Ratings of the players, computed with OpenSkill
(https://openskill.me), a rating system similar to TrueSkill.

Each player has an estimated skill (mu) and an uncertainty on this
estimation (sigma). After each game, the ratings of the players are
updated depending on the result (win, loss or draw) and on the ratings of
both teams: beating a stronger team gives more points, and the rating of
a new player (high sigma) changes faster than the one of a regular player.
The score difference of the game is not taken into account.

Each player has a global rating, computed from all their games and used to
create balanced teams, and a rating in each league, computed only from the
games of the league (starting from the initial score of the player).

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


def teams_of(game, players=None):
    """{'A': [players], 'B': [players]} of a game. `players` maps player ids
    to Player objects to use instead of loading them."""
    teams = {'A': [], 'B': []}
    for t in game.team_set.select_related('player').order_by('id'):
        teams[t.team_name].append(players[t.player_id] if players is not None else t.player)
    return teams


def update_ratings(teams, result, rating_of):
    """Update the ratings of the objects (players or league statistics, with
    mu, sigma and score attributes) of both teams after a game.

    rating_of(obj) gives the current (mu, sigma) of an object."""
    if not teams['A'] or not teams['B']:
        return
    ranks = {'A': [1, 2], 'B': [2, 1], 'draw': [1, 1]}[result]
    model_teams = [[MODEL.rating(*rating_of(obj)) for obj in teams[name]] for name in ('A', 'B')]
    new_teams = MODEL.rate(model_teams, ranks=ranks)
    for name, new_team in zip(('A', 'B'), new_teams):
        for obj, rating in zip(teams[name], new_team):
            obj.mu, obj.sigma = rating.mu, rating.sigma
            obj.score = display_score(rating.mu, rating.sigma)


def league_rating(stats):
    """(mu, sigma) of a player in a league. A player starts a league from
    their initial score."""
    if stats.mu is None or stats.sigma is None:
        return initial_rating(stats.player.initial_score)
    return stats.mu, stats.sigma


def rate_game(game, players=None):
    """Update the (global) ratings of the players of a completed game.

    `players` maps player ids to Player objects: when given, these objects
    are updated (and not saved), so that a sequence of games can be rated
    in memory. Otherwise, the players are loaded and saved.
    """
    teams = teams_of(game, players)
    update_ratings(teams, game_result(game), current_rating)
    if players is None:
        for player in teams['A'] + teams['B']:
            player.save(update_fields=['mu', 'sigma', 'score'])


def league_points(won, drawn):
    """Points in the standings of a league: 3 per win, 1 per draw."""
    return 3 if won else 1 if drawn else 0


def rate_game_in_league(game, stats_of):
    """Update the statistics of the players in the league of a completed
    game: win/loss/draw, points and rating in the league.

    stats_of(player) gives the PlayerStats of a player in the league of the
    game. The statistics are not saved."""
    teams = teams_of(game)
    league_teams = {name: [stats_of(p) for p in players] for name, players in teams.items()}
    result = game_result(game)
    update_ratings(league_teams, result, league_rating)
    for name, team in league_teams.items():
        for stats in team:
            if result == 'draw':
                stats.draw += 1
            elif result == name:
                stats.win += 1
            else:
                stats.loss += 1
            stats.total_points += league_points(result == name, result == 'draw')
    return league_teams['A'] + league_teams['B']


def complete_game(game):
    """Update the ratings and statistics of the players of a game that was
    just completed."""
    from .models import PlayerStats

    def stats_of(player):
        stats, created = PlayerStats.objects.get_or_create(player=player, league=game.league, owner=game.owner)
        return stats

    with transaction.atomic():
        rate_game(game)
        for stats in rate_game_in_league(game, stats_of):
            stats.save()


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
        stats = {}

        games = Game.objects.filter(completed=True).select_related('league').order_by(
            'completion_date', 'creation_date', 'id')
        for game in games:
            def stats_of(player):
                key = (player.id, game.league_id)
                if key not in stats:
                    stats[key] = PlayerStats(player=players[player.id], league=game.league, owner=game.owner)
                return stats[key]
            rate_game(game, players)
            rate_game_in_league(game, stats_of)

        Player.objects.bulk_update(players.values(), ['mu', 'sigma', 'score'])
        PlayerStats.objects.bulk_create(stats.values())
        return [(p, old_scores[pid], p.score) for pid, p in players.items()]
