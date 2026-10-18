# Upgrading PostgreSQL from 16 to 18

Until commit `b3e717b`, `docker-compose.yml` used PostgreSQL 16 with the
`postgres_data` volume. It now uses PostgreSQL 18 with a new volume,
`postgres18_data`. The data is not converted automatically: it must be
copied with a dump and a restore.

The old volume is not modified by this procedure, so you can go back to
PostgreSQL 16 if something goes wrong.

Run all the commands from the directory of the project, on the server.

## 1. Back up the PostgreSQL 16 database

Stop the website, so that nobody modifies the database during the upgrade:
```
docker-compose stop web
```

Write down the number of players, to check the restored database later:
```
docker-compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select count(*) from ultimate_ladder_player"'
```

Dump the database:
```
docker-compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > backup-pg16.sql
```

Check that the dump is complete (this should print `1`):
```
grep -c "PostgreSQL database dump complete" backup-pg16.sql
```

The dump contains all the data, including the password hashes: keep it
private (`*.sql` files are ignored by git).

## 2. Start PostgreSQL 18

```
docker-compose stop postgres
git pull
docker-compose up -d --wait postgres
```

`--wait` returns once PostgreSQL 18 has created the new, empty, database.

## 3. Restore the data

```
docker-compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q -v ON_ERROR_STOP=1 --single-transaction' < backup-pg16.sql
```

The restore is done in a single transaction: if an error occurs, nothing
is restored.

Check the version and the number of players (it should be the same as in
step 1):
```
docker-compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "show server_version" -c "select count(*) from ultimate_ladder_player"'
```

## 4. Restart the website

```
docker-compose up -d
```

## Going back to PostgreSQL 16

If something goes wrong, restore the previous `docker-compose.yml`. The
PostgreSQL 16 volume was not modified, but the changes made after the
upgrade are lost.
```
docker-compose stop
git checkout b3e717b -- docker-compose.yml
docker-compose up -d
```

## Cleaning up

Once the website has worked for a while with PostgreSQL 18, you can
delete the PostgreSQL 16 volume (its name is listed by
`docker volume ls | grep postgres_data`) and `backup-pg16.sql`. Keep a
copy of the backup somewhere else if you want.
