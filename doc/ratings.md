# Scores and standings

## Score of a player

The score of a player estimates their level. It is computed with
[OpenSkill](https://openskill.me), a rating system similar to TrueSkill,
used by online games:

- each player has an estimated skill and an uncertainty on this estimation;
- after each game, the skills of the players are updated depending on the
  result (win, draw or loss) and on the level of both teams: beating a
  stronger team gives more points than beating a weaker one;
- the score of a new player changes quickly, and becomes more stable as
  they play more games;
- the score difference of the game (eg. 7-3 or 7-6) is not taken into
  account: only the result matters.

The displayed score is the estimated skill of the player, scaled so that a
new player starts at 1000. A draw between two teams of the same level does
not change the scores. When creating a player, you can
set an *initial score* to give an estimate of their level (more than 1000
for an experienced player, less for a beginner). The score is used to
create balanced teams.

The code is in `ultimate_ladder/rating.py`.

## Standings of a league

In a league, players get 3 points per win, 1 point per draw and 0 point per
loss. Players with the same number of points are ranked by their percentage
of wins.

## Recomputing the scores

The following command recomputes the scores and the standings of all the
players, by replaying all the completed games, starting from the initial
score of each player:
```
python manage.py recompute_ratings --dry-run   # display the new scores
python manage.py recompute_ratings             # save them
```

## Upgrading from the previous scoring system

Before October 2026, the score was computed from the score differences of
the games. To upgrade a running server, from the directory of the project:

1. Back up the database (see [upgrade-postgres-18.md](upgrade-postgres-18.md)
   for the `pg_dump` command).

2. Get the new code and rebuild the image (a new Python package is needed):
   ```
   git pull
   docker-compose up -d --build
   ```

3. Add the new fields to the database:
   ```
   docker-compose exec web python manage.py makemigrations ultimate_ladder
   docker-compose exec web python manage.py migrate
   ```

4. Check the new scores, then save them:
   ```
   docker-compose exec web python manage.py recompute_ratings --dry-run
   docker-compose exec web python manage.py recompute_ratings
   ```

The initial score of the existing players is set to 1000. To give a
different starting point to some players, edit their initial score and run
`recompute_ratings` again.
