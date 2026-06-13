# analytis

Football analytics backend — pre-match probabilistic predictions for **1X2**, **Over/Under 2.5 goals** and **BTTS**, plus **value-bet discovery** by comparing model probabilities to live bookmaker odds, **Kelly fractional staking**, and **Closing Line Value (CLV)** tracking.

## Status

**Plans 1 + 2 + 3 of 4 complete.**

- Plan 1: Foundation + Ingestion (Postgres modelado, CLI/API, Football-Data.org + ELO + martj42 international results adapters).
- Plan 2: Features + Dixon-Coles (catálogo de features, Dixon-Coles fitter L-BFGS com shrinkage por confederação, walk-forward backtest, primeiras previsões 1X2/OU/BTTS).
- **Plan 3: Odds + Ensemble + Value Bets** (The Odds API adapter, EV math, Kelly fracional, bootstrap CI, isotonic calibration, XGBoost classifier + regressor + stacking ensemble, value-bet discovery, CLV tracker, rotas API novas).

Plan 4 (LLM news extractor, final backtest pipeline, in-play modelling) is the next milestone.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker Desktop (for Postgres)
- [Football-Data.org](https://www.football-data.org/) free API token (Copa fixtures + results)
- [The Odds API](https://the-odds-api.com/) free API token (~500 req/month, bookmaker odds)

## Setup

```bash
git clone <repo> && cd analytis
uv sync
cp .env.example .env
# edit .env: set ANALYTIS_FOOTBALL_DATA_API_KEY, ANALYTIS_THE_ODDS_API_KEY,
#            and ANALYTIS_API_KEY

docker compose up -d postgres
uv run analytis db migrate
```

Postgres is bound to host port **5434** (avoids conflict with Windows-installed Postgres).

## End-to-end workflow

```bash
# 1. Ingest current Copa 2026 fixtures (from Football-Data.org)
uv run analytis ingest fixtures --competition 2000 --season 2026

# 2. Ingest international history (martj42 CSV — free, ~45k matches)
uv run analytis ingest history --tournament "FIFA World Cup" --since 2010-01-01

# 3. Train Dixon-Coles
uv run analytis train dixon-coles \
    --since 2014-01-01 \
    --name dc-wc-v0.2.0-no-decay \
    --decay-per-day 0.0

# 4. Score all upcoming Copa 2026 matches
uv run analytis score all-upcoming --model dc-wc-v0.2.0-no-decay

# 5. Ingest current odds from The Odds API
uv run analytis odds fetch

# 6. Find +EV bets for a specific match
uv run analytis bets find-value \
    --match-id <match-uuid> \
    --model dc-wc-v0.2.0-no-decay \
    --min-edge 0.03 \
    --bankroll 1000 \
    --fraction 0.25 \
    --max-units 50

# 7. After the line moves (close to kickoff), re-fetch odds and track CLV
uv run analytis odds fetch
uv run analytis bets track-clv --match-id <match-uuid>

# 8. (Optional) Train XGBoost classifier from feature snapshots
uv run analytis train xgboost \
    --since 2014-01-01 \
    --name xgb-wc-v0.1.0 \
    --market 1x2

# 9. Walk-forward backtest
uv run analytis backtest run \
    --since 2014-01-01 \
    --min-train-size 128 \
    --test-size 32 \
    --decay-per-day 0.0
```

## HTTP API

```bash
uv run analytis api serve --port 8000

# Health (no auth)
curl http://localhost:8000/v1/health

# Predictions for a match
curl -H "X-API-Key: $ANALYTIS_API_KEY" \
    http://localhost:8000/v1/matches/<uuid>/predictions

# Latest odds (best per outcome)
curl -H "X-API-Key: $ANALYTIS_API_KEY" \
    http://localhost:8000/v1/matches/<uuid>/odds

# Persisted value bets for a match
curl -H "X-API-Key: $ANALYTIS_API_KEY" \
    http://localhost:8000/v1/matches/<uuid>/value-bets

# Aggregate CLV per model
curl -H "X-API-Key: $ANALYTIS_API_KEY" \
    http://localhost:8000/v1/bets/clv-summary

# List trained models
curl -H "X-API-Key: $ANALYTIS_API_KEY" \
    http://localhost:8000/v1/models
```

## ⚠️ Honest disclaimers (read before betting)

- **The current Dixon-Coles model is overconfident.** It was trained on ~200 World Cup matches and tends to produce edges of 50–90% on niche outcomes, which is almost certainly model error, not market mispricing.
- **CLV is the only honest measure of skill.** A positive edge on paper means nothing until you've ingested closing odds and `analytis bets track-clv` reports `closing_clv >= 0` over hundreds of bets.
- **Pinnacle is not in the free tier of The Odds API.** Comparing against secondary books (Smarkets, Betfair Exchange, etc.) is less informative than comparing against the sharpest line.
- **Stake conservatively.** Use **quarter Kelly** (default) or **flat tiny stakes** until you've collected at least 200 bets with positive CLV. The `kelly_stake_units` function caps stakes; don't lift the cap before you have evidence.
- **This is a tool, not a tipster.** The system shows you what its model thinks; whether to bet is your call.

## Tests

```bash
uv run pytest                          # all tests
uv run pytest -m "not integration"     # unit only (no docker)
uv run pytest -m integration -v        # integration only
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
├── domain/              # Pydantic entities
│   ├── competition.py, season.py, team.py, player.py, venue.py, referee.py
│   ├── match.py, ingestion.py, snapshots.py
│   ├── elo.py, confederation.py
│   └── odds.py
├── persistence/         # SQLAlchemy ORM + repositories
├── ingestion/           # adapters (Football-Data, ELO, martj42, The Odds API)
├── features/            # registry, elo math, strength, form, context, builder
├── modeling/            # Dixon-Coles, XGBoost, ensemble, isotonic, bootstrap, EV, Kelly, markets
├── application/         # use cases (ingest, train, score, backtest, value bets, CLV)
├── api/                 # FastAPI routes (health, predictions, models, odds, value-bets)
└── cli/                 # Typer subcommands (db, api, ingest, train, score, backtest, odds, bets)
```

## Plan 3 acceptance check

```bash
# Odds ingested for Copa 2026 matches
docker exec analytis-postgres psql -U analytis -d analytis \
    -c "SELECT market, COUNT(DISTINCT match_id) AS matches, COUNT(DISTINCT bookmaker) AS books, COUNT(*) AS quotes FROM odds_snapshot GROUP BY market;"

# Value bets discovered with non-negative edge / stake
docker exec analytis-postgres psql -U analytis -d analytis \
    -c "SELECT COUNT(*), ROUND(AVG(edge)::numeric, 3) AS avg_edge, ROUND(AVG(suggested_stake_units)::numeric, 1) AS avg_stake FROM value_bet WHERE edge > 0;"
```

## License

Proprietary — see project owner.
