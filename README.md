# MLB Database & API

A personal MLB statistics database and FastAPI service for custom at-bat-level split queries.

## What It Does

- Ingests completed MLB games from the MLB Stats API.
- Stores games, players, teams, parks, at-bats, pitch sequences, and steal attempts in PostgreSQL.
- Exposes reference endpoints for players, teams, and games.
- Exposes stats endpoints for batting, pitching, and stolen-base queries.
- Serves a small browser UI at `/`.

## API

- `GET /health`
- `GET /api/v1/players`
- `GET /api/v1/players/{mlb_id}`
- `GET /api/v1/teams`
- `GET /api/v1/teams/{mlb_id}`
- `GET /api/v1/games`
- `GET /api/v1/games/{mlb_game_id}`
- `POST /api/v1/stats/batting`
- `POST /api/v1/stats/pitching`
- `POST /api/v1/stats/steals`

Interactive docs are available at `/docs` when the app is running.

## Local Development

```bash
pip install -r requirements.txt
python -m scripts.create_tables
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run tests:

```bash
pytest
```

## Ingestion

Create tables:

```bash
python -m scripts.create_tables
```

Backfill historical data:

```bash
python -m scripts.run_backfill --start-year 2021
```

Sync one day, defaulting to yesterday:

```bash
python -m scripts.run_sync
python -m scripts.run_sync --date 2026-05-24
```

## GitHub Actions

`.github/workflows/build.yml` runs tests and builds the Docker image. On pushes to `main`, it also publishes:

```text
ghcr.io/<owner>/<repo>:latest
ghcr.io/<owner>/<repo>:sha-<commit>
```

If the GitHub repo is private, make sure the package visibility and Portainer registry credentials allow the homelab host to pull from GHCR.

## Portainer Deployment

Use `portainer-stack.yml` in Portainer. The stack follows the same homelab pattern as the investment app:

- one `mlbapi` app container
- attached to the existing external `homelab_network`
- routed by Traefik at `mlbapi.nawx.app`
- connected to the existing shared PostgreSQL container named `postgresql`

It does not create or run its own Postgres container.

Required Portainer environment variables:

```env
POSTGRES_PASSWORD=use-a-real-password
```

Recommended values:

```env
MLBAPI_IMAGE=ghcr.io/jnawx/mlbapi:latest
POSTGRES_HOST=postgresql
POSTGRES_PORT=5432
POSTGRES_DB=mlbapi
POSTGRES_USER=mlbapi
TZ=America/Phoenix
```

The `POSTGRES_PASSWORD` value is the password for the `mlbapi` database role, not the admin `gitlab` role from the shared Postgres stack.

The existing Postgres service should look roughly like this from the app's point of view:

```yaml
services:
  postgresql:
    container_name: postgresql
    hostname: postgresql
    networks:
      - homelab_network
```

If the `mlbapi` database/user do not already exist on that shared Postgres instance, create them once with the admin role:

```bash
docker exec -it postgresql psql -U gitlab -d gitlabhq_production
```

Then run:

```sql
CREATE USER mlbapi WITH PASSWORD 'use-a-real-password';
CREATE DATABASE mlbapi OWNER mlbapi;
GRANT ALL PRIVILEGES ON DATABASE mlbapi TO mlbapi;
```

The app container will create the MLB tables on startup when `RUN_DB_MIGRATIONS=true`.

## Local Build Stack

`portainer-stack.local-build.yml` is included for standalone Docker Compose/Portainer setups that build from the Git repo directly instead of pulling from GHCR.
