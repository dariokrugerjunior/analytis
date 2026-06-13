# analytis

Football analytics backend platform — pre-match probabilistic predictions for **1X2**, **Over/Under 2.5 goals**, and **BTTS** markets, with **Dixon-Coles** modeling, **Bayesian shrinkage by FIFA confederation**, **walk-forward cross-validation**, and **calibration metrics** as first-class outputs.

## Status

**Plans 1 + 2 of 4 complete.**
- Plan 1: Foundation + Ingestion (Postgres modelado, CLI/API, Football-Data.org + ELO + martj42 international results adapters).
- Plan 2: Features + Dixon-Coles + first probabilistic predictions persisted in `prediction` table + walk-forward backtest + API routes for predictions and models.

Plans 3-4 (XGBoost ensemble, Bayesian uncertainty layer, LLM news extractor) are in the roadmap.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker Desktop (for Postgres)
- A [Football-Data.org](https://www.football-data.org/) free API token (for live Copa 2026 fixtures)

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

## End-to-end workflow

```bash
# 1. Ingest current Copa 2026 fixtures from Football-Data.org
uv run analytis ingest fixtures --competition 2000 --season 2026

# 2. Ingest international history from the open martj42/international_results CSV
uv run analytis ingest history --tournament "FIFA World Cup" --since 2010-01-01

# 3. Train a Dixon-Coles model on the historical matches
uv run analytis train dixon-coles \
    --since 2010-01-01 \
    --name dc-wc-v0.1.0 \
    --max-iter 300 \
    --decay-per-day 0.001

# 4. Score all upcoming Copa 2026 matches
uv run analytis score all-upcoming --model dc-wc-v0.1.0

# 5. Run a walk-forward backtest against historical World Cups
uv run analytis backtest run \
    --since 2010-01-01 \
    --until 2026-01-01 \
    --min-train-size 128 \
    --test-size 32 \
    --decay-per-day 0.0
```

## HTTP API

```bash
# Serve
uv run analytis api serve --port 8000

# Health
curl http://localhost:8000/v1/health

# Predictions for a match
curl -H "X-API-Key: $ANALYTIS_API_KEY" \
    http://localhost:8000/v1/matches/<match-uuid>/predictions

# List trained models
curl -H "X-API-Key: $ANALYTIS_API_KEY" \
    http://localhost:8000/v1/models

# Model metrics
curl -H "X-API-Key: $ANALYTIS_API_KEY" \
    http://localhost:8000/v1/models/<version-uuid>/metrics
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
│   ├── competition.py, season.py, team.py, player.py, venue.py, referee.py
│   ├── match.py, ingestion.py, snapshots.py
│   ├── elo.py, confederation.py
├── persistence/         # SQLAlchemy ORM + repositories
├── ingestion/           # adapters (Football-Data, ELO, martj42 CSV), pipeline, scheduler
├── application/         # use cases (ingest, train, score, backtest, compute_elo_history)
├── features/            # registry, elo math, strength (shrinkage), form (decay), context, builder
├── modeling/            # Dixon-Coles math, fitter (L-BFGS), markets, prior, evaluation, walk-forward
├── api/                 # FastAPI routes (health, predictions, models)
└── cli/                 # Typer (db, api, ingest, train, score, backtest)
```

## Plan 2 acceptance check

Run these to confirm Plan 2 is delivering as expected:

```bash
# Historical matches loaded (>= 192 expected: 64 × {2010, 2014, 2018})
docker exec analytis-postgres psql -U analytis -d analytis \
    -c "SELECT COUNT(*) FROM match m JOIN season s ON s.id=m.season_id JOIN competition c ON c.id=s.competition_id WHERE c.slug='fifa-world-cup-history';"

# Trained model exists with metrics
docker exec analytis-postgres psql -U analytis -d analytis \
    -c "SELECT name, hyperparams->'decay_per_day' AS decay, metrics->>'home_advantage' AS ha, metrics->>'rho' AS rho FROM model_version;"

# Predictions stored
docker exec analytis-postgres psql -U analytis -d analytis \
    -c "SELECT market, COUNT(*) FROM prediction GROUP BY market;"
```

## License

Proprietary — see project owner.
