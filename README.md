# analytis

Football analytics backend platform — pre-match probabilistic predictions for 1X2, Over/Under goals, BTTS and corners markets.

## Status

**Plan 1 of 4 — Foundation + Ingestion.** Pre-match probabilistic models, API key auth, full prediction pipeline still under construction. See `docs/superpowers/specs/2026-06-12-football-analytics-design.md`.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker Desktop (for Postgres)
- A [Football-Data.org](https://www.football-data.org/) free API token

## Setup

```bash
git clone <repo> && cd analytis
uv sync
cp .env.example .env
# edit .env: set ANALYTIS_FOOTBALL_DATA_API_KEY and ANALYTIS_API_KEY

docker compose up -d postgres
uv run analytis db migrate
```

**Note on Postgres port:** the compose file binds Postgres to host port **5434** (not the default 5432) to avoid conflict with a Windows-installed Postgres service. The `.env.example` already reflects this. If you have no local Postgres install, you can change the binding back to 5432 in `docker-compose.yml`.

## Common operations

```bash
# HTTP API
uv run analytis api serve --port 8000
curl -H "X-API-Key: $ANALYTIS_API_KEY" http://localhost:8000/v1/health

# Ingest the World Cup 2026 fixtures + results so far
uv run analytis ingest fixtures --competition 2000 --season 2026

# Backfill historical World Cups
uv run analytis ingest backfill --competition 2000 --season 2018 --season 2022
```

## Tests

```bash
uv run pytest                          # all tests
uv run pytest -m "not integration"     # unit only (no docker)
uv run pytest -m integration -v        # integration only (testcontainers)
```

## Quality

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pre-commit run --all-files
```

## Layout

```
src/analytis/
├── config.py            # Pydantic Settings (env-driven)
├── logging.py           # structlog setup
├── domain/              # Pydantic entities (pure, no I/O)
├── persistence/         # SQLAlchemy ORM + repositories
├── ingestion/           # adapters, rate limit, retry, pipeline, scheduler
├── application/         # use cases (orchestration)
├── api/                 # FastAPI routes
└── cli/                 # Typer subcommands
```

## License

Proprietary — see project owner.
