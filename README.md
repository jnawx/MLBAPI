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

Use `portainer-stack.yml` for a normal Portainer stack that publishes the API on a host port, then point your reverse proxy at it.

Required Portainer environment variables:

```env
POSTGRES_PASSWORD=use-a-real-password
MLBAPI_IMAGE=ghcr.io/<owner>/<repo>:latest
```

Recommended values:

```env
POSTGRES_DB=mlbapi
POSTGRES_USER=mlbapi
MLBAPI_PORT=8000
TZ=America/Phoenix
```

Then route:

```text
https://mlb.api.nawx.app -> http://<docker-host>:8000
```

## Portainer With Traefik

If your homelab uses Traefik, deploy `portainer-stack.traefik.yml` instead.

Required:

```env
POSTGRES_PASSWORD=use-a-real-password
MLBAPI_IMAGE=ghcr.io/<owner>/<repo>:latest
```

Common Traefik values:

```env
MLBAPI_HOST=mlb.api.nawx.app
TRAEFIK_NETWORK=proxy
TRAEFIK_ENTRYPOINT=websecure
TRAEFIK_CERT_RESOLVER=letsencrypt
```

The Traefik network must already exist, for example:

```bash
docker network create proxy
```

## Local Build Stack

`portainer-stack.local-build.yml` is included for standalone Docker Compose/Portainer setups that build from the Git repo directly instead of pulling from GHCR.

