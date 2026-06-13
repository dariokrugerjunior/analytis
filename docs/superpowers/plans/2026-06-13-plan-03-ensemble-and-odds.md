# Plano 3 — Odds, Ensemble e Apostas com Valor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar o sistema utilizável para apostas reais: ingerir odds de bookmakers (The Odds API), calcular Expected Value, gerar intervalos de credibilidade por bootstrap, complementar Dixon-Coles com XGBoost em ensemble calibrado, recomendar tamanho de aposta via Kelly fracionado e rastrear Closing Line Value (CLV) como métrica honesta de skill.

**Architecture:** Novo adapter `TheOddsApiAdapter` para uma fonte gratuita de odds (≤500 req/mês free tier). Tabela `odds_snapshot` armazenando odds por (match × mercado × outcome × bookmaker × snapshot_taken_at), imutável. Bootstrap resampling sobre o `fit_dixon_coles` substitui os CIs simplistas atuais. `XGBoostClassifier` e `XGBoostRegressor` treinam sobre o vetor de features já produzido em Plano 2 e suas predições são combinadas por stacking (regressão logística meta). Isotonic regression calibra probs por mercado. `find_value_bets` compara nossa prob com a melhor odds disponível e marca os +EV; `track_clv` mede skill após o jogo. CLI e API novas expõem tudo.

**Tech Stack:** Existente (Python 3.12, uv, Ruff, Mypy strict, Pytest+hypothesis+respx+testcontainers, FastAPI, SQLAlchemy 2.x async, Pydantic 2, Alembic, Typer, httpx, structlog, numpy, scipy, pandas, pyarrow) + **novos**: `xgboost>=2.1`, `scikit-learn>=1.5`.

**Branch:** trabalhar direto em `main` (preferência do usuário do Plano 2).

**Spec:** `docs/superpowers/specs/2026-06-12-football-analytics-design.md` §7 (modelagem), §8 (scoring), §11 sem 5-6.

---

## Estrutura de arquivos do plano

```
analytis/
├── migrations/versions/
│   └── 0003_odds_and_bets.py                  # odds_snapshot, value_bet
├── src/analytis/
│   ├── domain/
│   │   ├── odds.py                            # OddsQuote, BookmakerKey
│   │   └── bet.py                             # ValueBet entity
│   ├── persistence/orm/
│   │   ├── odds.py                            # OddsSnapshotORM
│   │   └── bets.py                            # ValueBetORM
│   ├── persistence/repositories/
│   │   ├── odds.py                            # OddsRepository
│   │   └── bets.py                            # ValueBetRepository
│   ├── ingestion/adapters/
│   │   └── the_odds_api.py                    # The Odds API REST adapter
│   ├── application/
│   │   ├── ingest_odds.py                     # use case
│   │   ├── find_value_bets.py                 # use case
│   │   ├── track_clv.py                       # use case
│   │   └── train_xgboost.py                   # XGBoost training use case
│   ├── modeling/
│   │   ├── bootstrap.py                       # bootstrap resampling
│   │   ├── ensemble.py                        # stacking meta-model
│   │   ├── xgboost_classifier.py
│   │   ├── xgboost_regressor.py
│   │   ├── isotonic.py                        # isotonic calibration
│   │   ├── kelly.py                           # fractional Kelly stake
│   │   ├── corners.py                         # Poisson bivariado para escanteios
│   │   └── ev.py                              # EV math
│   ├── cli/
│   │   ├── odds.py                            # analytis odds fetch
│   │   └── bets.py                            # analytis bets find-value, track-clv
│   └── api/routes/
│       ├── odds.py                            # /v1/odds
│       └── value_bets.py                      # /v1/value-bets
└── tests/
    ├── unit/
    │   ├── modeling/
    │   │   ├── test_bootstrap.py
    │   │   ├── test_ensemble.py
    │   │   ├── test_isotonic.py
    │   │   ├── test_kelly.py
    │   │   ├── test_ev.py
    │   │   └── test_corners.py
    │   ├── ingestion/adapters/test_the_odds_api.py
    │   ├── domain/test_odds.py
    │   └── domain/test_bet.py
    └── integration/
        ├── ingestion/test_odds_ingestion.py
        ├── application/test_find_value_bets.py
        ├── application/test_track_clv.py
        ├── application/test_train_xgboost.py
        ├── api/test_odds_route.py
        └── api/test_value_bets_route.py
```

---

## Convenções gerais

- Python 3.12+; sem `from __future__ import annotations`.
- TDD obrigatório no que produz output mensurável (domain, modeling, application). Não-TDD apenas em migrations Alembic, ORM puro, wiring CLI/API.
- Commits frequentes, isolados por task. Mensagens em inglês `<type>: <message>`.
- **NÃO** adicionar trailer `Co-Authored-By: Claude...`.
- uv path prepended em todo Bash:
  ```bash
  export PATH="/c/Users/PC Gamer/AppData/Local/Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe:$PATH"
  ```
- env vars:
  ```bash
  export ANALYTIS_DATABASE_URL="postgresql+psycopg://analytis:analytis_dev@localhost:5434/analytis"
  export ANALYTIS_API_KEY="local-dev-change-me"
  ```
- Sandbox bloqueia commits diretos em main para subagents — staged-only; parent commits.
- Já existem 30 commits em main do Plano 2.

---

## Task 1: Adicionar dependências ML (xgboost, scikit-learn) + The Odds API config

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/analytis/config.py`
- Modify: `.env.example`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Estender `pyproject.toml` runtime deps**

Localize a lista `dependencies = [...]` e adicione (em ordem alfabética):

```toml
    "scikit-learn>=1.5.0",
    "xgboost>=2.1.0",
```

- [ ] **Step 2: Estender `src/analytis/config.py` com The Odds API**

Adicione 2 campos na classe `Settings`:

```python
    the_odds_api_key: SecretStr | None = None
    the_odds_api_base_url: str = "https://api.the-odds-api.com/v4"
```

- [ ] **Step 3: Atualizar `.env.example`**

Adicione no final:

```
# The Odds API (free tier ~500 req/month)
ANALYTIS_THE_ODDS_API_KEY=
ANALYTIS_THE_ODDS_API_BASE_URL=https://api.the-odds-api.com/v4
```

- [ ] **Step 4: Acrescentar teste em `tests/unit/test_config.py`**

```python
def test_settings_loads_optional_odds_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANALYTIS_DATABASE_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("ANALYTIS_API_KEY", "x")
    monkeypatch.setenv("ANALYTIS_THE_ODDS_API_KEY", "abc123")

    settings = Settings()
    assert settings.the_odds_api_key is not None
    assert settings.the_odds_api_key.get_secret_value() == "abc123"
    assert settings.the_odds_api_base_url.startswith("https://")
```

- [ ] **Step 5: Sync + validate**

```bash
export PATH="/c/Users/PC Gamer/AppData/Local/Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe:$PATH"
uv sync
uv run python -c "import xgboost, sklearn; print(xgboost.__version__, sklearn.__version__)"
uv run pytest tests/unit/test_config.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: ML versions print; 4 config tests pass; clean.

- [ ] **Step 6: Stage**

```bash
git add pyproject.toml uv.lock src/analytis/config.py .env.example tests/unit/test_config.py
```

---

## Task 2: Domain entities — OddsQuote, BookmakerKey

**Files:**
- Create: `src/analytis/domain/odds.py`
- Test: `tests/unit/domain/test_odds.py`

- [ ] **Step 1: Write test — `tests/unit/domain/test_odds.py`**

```python
"""Tests for OddsQuote domain entity."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from analytis.domain.odds import BookmakerKey, OddsQuote


def test_odds_quote_minimal() -> None:
    q = OddsQuote(
        match_id=uuid4(),
        bookmaker=BookmakerKey("pinnacle"),
        market="1x2",
        outcome="home",
        decimal_odds=2.10,
        snapshot_taken_at=datetime(2026, 6, 13, tzinfo=UTC),
    )
    assert q.decimal_odds == 2.10
    assert q.implied_probability() == pytest.approx(1.0 / 2.10, abs=1e-9)


def test_odds_quote_rejects_decimal_below_one() -> None:
    with pytest.raises(ValueError, match="decimal_odds must be >= 1.01"):
        OddsQuote(
            match_id=uuid4(),
            bookmaker=BookmakerKey("any"),
            market="1x2",
            outcome="home",
            decimal_odds=0.99,
            snapshot_taken_at=datetime(2026, 6, 13, tzinfo=UTC),
        )


def test_odds_quote_naive_snapshot_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        OddsQuote(
            match_id=uuid4(),
            bookmaker=BookmakerKey("any"),
            market="1x2",
            outcome="home",
            decimal_odds=2.0,
            snapshot_taken_at=datetime(2026, 6, 13),
        )


def test_bookmaker_key_normalises() -> None:
    assert BookmakerKey("  PinNacle  ") == "pinnacle"
    assert BookmakerKey("BET 365") == "bet_365"


def test_bookmaker_key_rejects_empty() -> None:
    with pytest.raises(ValueError, match="bookmaker key"):
        BookmakerKey("")
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/domain/test_odds.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/analytis/domain/odds.py`**

```python
"""Odds quote domain entity."""

import re
from datetime import datetime
from typing import NewType
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from analytis.domain.ids import MatchId


def _normalise_key(value: str) -> str:
    cleaned = value.strip().lower()
    if not cleaned:
        raise ValueError("bookmaker key cannot be empty")
    return re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")


class _BookmakerKeyMeta(type):
    def __call__(cls, value: str) -> str:  # type: ignore[override]
        return _normalise_key(value)


class BookmakerKey(str, metaclass=_BookmakerKeyMeta):
    """Normalised bookmaker identifier (lowercase, alnum, underscore-separated)."""


class OddsQuote(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: MatchId = Field(default_factory=uuid4)
    match_id: MatchId
    bookmaker: str = Field(min_length=1, max_length=50)
    market: str = Field(min_length=1, max_length=50)
    outcome: str = Field(min_length=1, max_length=50)
    decimal_odds: float = Field(ge=1.01, le=1000.0)
    snapshot_taken_at: datetime

    @model_validator(mode="after")
    def _validate(self) -> "OddsQuote":
        if self.decimal_odds < 1.01:
            raise ValueError("decimal_odds must be >= 1.01")
        if self.snapshot_taken_at.tzinfo is None:
            raise ValueError("snapshot_taken_at must be timezone-aware")
        return self

    def implied_probability(self) -> float:
        """Naive implied probability (does NOT remove overround)."""
        return 1.0 / self.decimal_odds


__all__ = ["BookmakerKey", "OddsQuote"]
```

- [ ] **Step 4: Run tests + quality**

```bash
uv run pytest tests/unit/domain/test_odds.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 5 tests pass.

- [ ] **Step 5: Stage**

```bash
git add src/analytis/domain/odds.py tests/unit/domain/test_odds.py
```

---

## Task 3: ORM + migration 0003 (odds_snapshot + value_bet placeholder)

**Files:**
- Create: `src/analytis/persistence/orm/odds.py`
- Create: `src/analytis/persistence/orm/bets.py`
- Modify: `src/analytis/persistence/orm/__init__.py`
- Create: `migrations/versions/0003_odds_and_bets.py` (autogenerated)

- [ ] **Step 1: Create `src/analytis/persistence/orm/odds.py`**

```python
"""ORM for odds snapshots."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from analytis.persistence.orm.base import Base, TimestampMixin


class OddsSnapshotORM(Base, TimestampMixin):
    __tablename__ = "odds_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "bookmaker",
            "market",
            "outcome",
            "snapshot_taken_at",
            name="uq_odds_snapshot_natural",
        ),
        Index("ix_odds_snapshot_match_market", "match_id", "market"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("match.id", ondelete="CASCADE"),
        nullable=False,
    )
    bookmaker: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    decimal_odds: Mapped[float] = mapped_column(Float, nullable=False)
    snapshot_taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
```

- [ ] **Step 2: Create `src/analytis/persistence/orm/bets.py`**

```python
"""ORM for value bet recommendations + CLV tracking."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from analytis.persistence.orm.base import Base, TimestampMixin


class ValueBetORM(Base, TimestampMixin):
    __tablename__ = "value_bet"
    __table_args__ = (
        Index("ix_value_bet_match", "match_id"),
        Index("ix_value_bet_model", "model_version_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("match.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_version.id", ondelete="RESTRICT"),
        nullable=False,
    )
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    bookmaker: Mapped[str] = mapped_column(String(50), nullable=False)
    our_prob: Mapped[float] = mapped_column(Float, nullable=False)
    market_prob: Mapped[float] = mapped_column(Float, nullable=False)
    decimal_odds: Mapped[float] = mapped_column(Float, nullable=False)
    edge: Mapped[float] = mapped_column(Float, nullable=False)
    kelly_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    suggested_stake_units: Mapped[float] = mapped_column(Float, nullable=False)
    found_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closing_decimal_odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    closing_clv: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_realised: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
```

- [ ] **Step 3: Update `src/analytis/persistence/orm/__init__.py`**

Add imports + `__all__` entries (alphabetical):

```python
from analytis.persistence.orm.bets import ValueBetORM
from analytis.persistence.orm.odds import OddsSnapshotORM
```

Add `"OddsSnapshotORM"` and `"ValueBetORM"` to `__all__`.

- [ ] **Step 4: Generate Alembic migration**

```bash
export PATH="/c/Users/PC Gamer/AppData/Local/Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe:$PATH"
export ANALYTIS_DATABASE_URL="postgresql+psycopg://analytis:analytis_dev@localhost:5434/analytis"
export ANALYTIS_API_KEY="local-dev"
uv run alembic revision --autogenerate -m "odds and bets"
```

Rename generated file to `migrations/versions/0003_odds_and_bets.py`. In the file body:
- `revision: str = "0003"`
- `down_revision: str | Sequence[str] | None = "0002"`

- [ ] **Step 5: Apply migration**

```bash
uv run alembic upgrade head
docker exec analytis-postgres psql -U analytis -d analytis -c "\d odds_snapshot"
docker exec analytis-postgres psql -U analytis -d analytis -c "\d value_bet"
```

Expected: tables exist with their indexes.

- [ ] **Step 6: Validate quality**

```bash
uv run mypy src tests
uv run ruff check .
```

- [ ] **Step 7: Stage**

```bash
git add src/analytis/persistence/orm/odds.py src/analytis/persistence/orm/bets.py src/analytis/persistence/orm/__init__.py migrations/versions/0003_odds_and_bets.py
```

---

## Task 4: TheOddsApiAdapter

**Files:**
- Create: `src/analytis/ingestion/adapters/the_odds_api.py`
- Test: `tests/unit/ingestion/adapters/test_the_odds_api.py`

The API: `GET /v4/sports/soccer_fifa_world_cup/odds?apiKey=...&regions=eu&markets=h2h,totals,btts&oddsFormat=decimal`. Returns array of events, each with bookmakers list, each with markets list, each with outcomes list (`name`, `price`).

- [ ] **Step 1: Write test FIRST**

```python
"""Unit tests for The Odds API adapter."""

from datetime import UTC, datetime

import httpx
import pytest
import respx

from analytis.ingestion.adapters.the_odds_api import TheOddsApiAdapter

BASE = "https://api.the-odds-api.com/v4"


@pytest.mark.asyncio
async def test_fetch_odds_h2h_only() -> None:
    payload = [
        {
            "id": "ev1",
            "sport_key": "soccer_fifa_world_cup",
            "commence_time": "2026-06-13T22:00:00Z",
            "home_team": "Brazil",
            "away_team": "Morocco",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "title": "Pinnacle",
                    "last_update": "2026-06-13T15:00:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Brazil", "price": 2.40},
                                {"name": "Draw", "price": 3.10},
                                {"name": "Morocco", "price": 3.20},
                            ],
                        }
                    ],
                }
            ],
        }
    ]

    with respx.mock(base_url=BASE) as mock:
        mock.get("/sports/soccer_fifa_world_cup/odds").respond(200, json=payload)
        async with httpx.AsyncClient(base_url=BASE) as client:
            adapter = TheOddsApiAdapter(client=client, api_key="x")
            events = list(
                await adapter.fetch_odds(
                    sport_key="soccer_fifa_world_cup",
                    markets=("h2h",),
                )
            )

    assert len(events) == 1
    ev = events[0]
    assert ev.home_team == "Brazil"
    assert ev.away_team == "Morocco"
    assert ev.commence_time == datetime(2026, 6, 13, 22, 0, tzinfo=UTC)
    assert len(ev.bookmakers) == 1
    bm = ev.bookmakers[0]
    assert bm.key == "pinnacle"
    home_market = next(m for m in bm.markets if m.market_key == "h2h")
    home_outcome = next(o for o in home_market.outcomes if o.name == "Brazil")
    assert home_outcome.decimal_odds == 2.40
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/ingestion/adapters/test_the_odds_api.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/analytis/ingestion/adapters/the_odds_api.py`**

```python
"""Adapter for The Odds API (https://the-odds-api.com).

Free tier: ~500 requests/month. We hit the /odds endpoint per sport_key.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from analytis.ingestion.retry import with_retry


@dataclass(frozen=True)
class TheOddsOutcome:
    name: str
    decimal_odds: float


@dataclass(frozen=True)
class TheOddsMarket:
    market_key: str
    outcomes: list[TheOddsOutcome]


@dataclass(frozen=True)
class TheOddsBookmaker:
    key: str
    title: str
    last_update: datetime
    markets: list[TheOddsMarket]


@dataclass(frozen=True)
class TheOddsEvent:
    external_id: str
    sport_key: str
    commence_time: datetime
    home_team: str
    away_team: str
    bookmakers: list[TheOddsBookmaker]


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class TheOddsApiAdapter:
    source_id = "the_odds_api"

    def __init__(self, client: httpx.AsyncClient, api_key: str) -> None:
        self._client = client
        self._api_key = api_key

    @with_retry(max_attempts=3, base_delay=1.0)
    async def _get(self, path: str, **params: Any) -> Any:
        response = await self._client.get(
            path,
            params={"apiKey": self._api_key, **params},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    async def fetch_odds(
        self,
        *,
        sport_key: str = "soccer_fifa_world_cup",
        markets: tuple[str, ...] = ("h2h", "totals", "btts"),
        regions: str = "eu,us,uk",
    ) -> Iterable[TheOddsEvent]:
        data = await self._get(
            f"/sports/{sport_key}/odds",
            regions=regions,
            markets=",".join(markets),
            oddsFormat="decimal",
        )
        events: list[TheOddsEvent] = []
        for ev in data:
            bookmakers: list[TheOddsBookmaker] = []
            for bm in ev.get("bookmakers", []):
                ms: list[TheOddsMarket] = []
                for m in bm.get("markets", []):
                    outs = [
                        TheOddsOutcome(name=o["name"], decimal_odds=float(o["price"]))
                        for o in m.get("outcomes", [])
                    ]
                    ms.append(TheOddsMarket(market_key=m["key"], outcomes=outs))
                bookmakers.append(
                    TheOddsBookmaker(
                        key=bm["key"],
                        title=bm["title"],
                        last_update=_parse_iso(bm["last_update"]),
                        markets=ms,
                    )
                )
            events.append(
                TheOddsEvent(
                    external_id=ev["id"],
                    sport_key=ev["sport_key"],
                    commence_time=_parse_iso(ev["commence_time"]),
                    home_team=ev["home_team"],
                    away_team=ev["away_team"],
                    bookmakers=bookmakers,
                )
            )
        return events
```

- [ ] **Step 4: Run tests + quality**

```bash
uv run pytest tests/unit/ingestion/adapters/test_the_odds_api.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 1 test passes.

- [ ] **Step 5: Stage**

```bash
git add src/analytis/ingestion/adapters/the_odds_api.py tests/unit/ingestion/adapters/test_the_odds_api.py
```

---

## Task 5: OddsRepository + IngestOddsUseCase + CLI `analytis odds fetch`

**Files:**
- Create: `src/analytis/persistence/repositories/odds.py`
- Modify: `src/analytis/persistence/repositories/__init__.py`
- Create: `src/analytis/application/ingest_odds.py`
- Create: `src/analytis/cli/odds.py`
- Modify: `src/analytis/cli/app.py`
- Test: `tests/integration/ingestion/test_odds_ingestion.py`

- [ ] **Step 1: Create `src/analytis/persistence/repositories/odds.py`**

```python
"""Repository for OddsSnapshot."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.persistence.orm.odds import OddsSnapshotORM


class OddsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_quote(
        self,
        *,
        match_id: UUID,
        bookmaker: str,
        market: str,
        outcome: str,
        decimal_odds: float,
        snapshot_taken_at: datetime,
    ) -> bool:
        """Insert if (match, bm, market, outcome, taken_at) is new; else no-op.
        Returns True if a row was actually inserted."""
        stmt = pg_insert(OddsSnapshotORM).values(
            match_id=match_id,
            bookmaker=bookmaker,
            market=market,
            outcome=outcome,
            decimal_odds=decimal_odds,
            snapshot_taken_at=snapshot_taken_at,
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_odds_snapshot_natural"
        ).returning(OddsSnapshotORM.id)
        result = await self._session.execute(stmt)
        return result.scalar() is not None

    async def latest_for_match(
        self, match_id: UUID, market: str
    ) -> list[OddsSnapshotORM]:
        result = await self._session.scalars(
            select(OddsSnapshotORM).where(
                OddsSnapshotORM.match_id == match_id,
                OddsSnapshotORM.market == market,
            )
        )
        rows = list(result.all())
        latest_per_book: dict[tuple[str, str], OddsSnapshotORM] = {}
        for r in rows:
            key = (r.bookmaker, r.outcome)
            existing = latest_per_book.get(key)
            if existing is None or r.snapshot_taken_at > existing.snapshot_taken_at:
                latest_per_book[key] = r
        return list(latest_per_book.values())
```

- [ ] **Step 2: Update repositories `__init__.py`**

Add:

```python
from analytis.persistence.repositories.odds import OddsRepository
```

Add `"OddsRepository"` to `__all__` (alphabetical).

- [ ] **Step 3: Create `src/analytis/application/ingest_odds.py`**

```python
"""Use case: ingest odds from The Odds API into our DB."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.ingestion.adapters.the_odds_api import TheOddsApiAdapter
from analytis.ingestion.pipeline import IngestionPipeline, IngestionResult
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.repositories import OddsRepository
from analytis.persistence.unit_of_work import UnitOfWork


_MARKET_KEY_MAP = {
    "h2h": "1x2",
    "totals": "over_under_goals",
    "btts": "btts",
}


_OUTCOME_NAME_MAP_H2H = {
    "draw": "draw",
}


def _outcome_for_h2h(name: str, home: str, away: str) -> str | None:
    n = name.strip().lower()
    if n == home.lower():
        return "home"
    if n == away.lower():
        return "away"
    return _OUTCOME_NAME_MAP_H2H.get(n)


def _outcome_for_totals(name: str, point: float | None) -> str | None:
    n = name.strip().lower()
    if point is None:
        return None
    line = str(point).rstrip("0").rstrip(".")
    if n.startswith("over"):
        return f"over_{line}"
    if n.startswith("under"):
        return f"under_{line}"
    return None


@dataclass(frozen=True)
class IngestOddsParams:
    sport_key: str = "soccer_fifa_world_cup"


@dataclass
class IngestOddsResult:
    matches_matched: int
    quotes_inserted: int
    quotes_skipped: int


class IngestOddsUseCase:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        adapter: TheOddsApiAdapter,
    ) -> None:
        self._factory = session_factory
        self._adapter = adapter
        self._pipeline = IngestionPipeline(session_factory, adapter.source_id)

    async def execute(self, params: IngestOddsParams) -> IngestionResult:
        async def job(uow: UnitOfWork) -> IngestionResult:
            events = list(
                await self._adapter.fetch_odds(sport_key=params.sport_key)
            )
            odds_repo = OddsRepository(uow.session)

            # Build (home_lower, away_lower) -> match_id lookup
            team_rows = (
                await uow.session.execute(select(TeamORM.id, TeamORM.name))
            ).all()
            name_to_id = {r.name.lower(): r.id for r in team_rows}

            match_rows = (
                await uow.session.execute(
                    select(MatchORM).where(MatchORM.status.in_(("scheduled", "live")))
                )
            ).scalars().all()

            inserted = 0
            skipped = 0
            matched = 0
            for ev in events:
                home_id = name_to_id.get(ev.home_team.lower())
                away_id = name_to_id.get(ev.away_team.lower())
                if home_id is None or away_id is None:
                    skipped += 1
                    continue
                match = next(
                    (
                        m for m in match_rows
                        if m.home_team_id == home_id and m.away_team_id == away_id
                    ),
                    None,
                )
                if match is None:
                    skipped += 1
                    continue
                matched += 1
                for bm in ev.bookmakers:
                    for m in bm.markets:
                        canonical_market = _MARKET_KEY_MAP.get(m.market_key)
                        if canonical_market is None:
                            continue
                        for o in m.outcomes:
                            if canonical_market == "1x2":
                                outcome = _outcome_for_h2h(
                                    o.name, ev.home_team, ev.away_team
                                )
                            elif canonical_market == "over_under_goals":
                                outcome = _outcome_for_totals(o.name, None)
                            elif canonical_market == "btts":
                                outcome = (
                                    "yes"
                                    if o.name.strip().lower() == "yes"
                                    else "no"
                                )
                            else:
                                outcome = None
                            if outcome is None:
                                continue
                            ok = await odds_repo.insert_quote(
                                match_id=match.id,
                                bookmaker=bm.key,
                                market=canonical_market,
                                outcome=outcome,
                                decimal_odds=o.decimal_odds,
                                snapshot_taken_at=bm.last_update,
                            )
                            if ok:
                                inserted += 1
            return IngestionResult(records_touched=inserted)

        return await self._pipeline.run(
            job_name=f"ingest:odds:{params.sport_key}",
            job=job,
        )
```

- [ ] **Step 4: Create `src/analytis/cli/odds.py`**

```python
"""CLI for odds ingestion."""

import asyncio

import httpx
import typer
from rich.console import Console

from analytis.application.ingest_odds import IngestOddsParams, IngestOddsUseCase
from analytis.config import get_settings
from analytis.ingestion.adapters.the_odds_api import TheOddsApiAdapter
from analytis.persistence.engine import create_engine, create_session_factory

app = typer.Typer(help="Odds ingestion.")
console = Console()


@app.command("fetch")
def fetch(
    sport_key: str = typer.Option(
        "soccer_fifa_world_cup",
        "--sport",
        help="The Odds API sport key.",
    ),
) -> None:
    """Fetch current odds from The Odds API."""
    asyncio.run(_fetch(sport_key))


async def _fetch(sport_key: str) -> None:
    settings = get_settings()
    if settings.the_odds_api_key is None:
        console.print("[red]ANALYTIS_THE_ODDS_API_KEY not set[/red]")
        raise typer.Exit(code=2)
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with httpx.AsyncClient(
            base_url=settings.the_odds_api_base_url
        ) as client:
            adapter = TheOddsApiAdapter(
                client=client,
                api_key=settings.the_odds_api_key.get_secret_value(),
            )
            use_case = IngestOddsUseCase(factory, adapter)
            result = await use_case.execute(IngestOddsParams(sport_key=sport_key))
        console.print(
            f"[green]Inserted {result.records_touched} new odds quotes.[/green]"
        )
    finally:
        await engine.dispose()
```

- [ ] **Step 5: Register in `src/analytis/cli/app.py`**

Add `odds` to imports + add_typer line:

```python
from analytis.cli import api, backtest, db, ingest, odds, score, train

app.add_typer(odds.app, name="odds", help="Odds ingestion.")
```

- [ ] **Step 6: Write integration test (use a fake adapter to keep it offline)**

```python
"""Integration test for odds ingestion."""

from collections.abc import Iterable
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.ingest_odds import IngestOddsParams, IngestOddsUseCase
from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.ingestion.adapters.the_odds_api import (
    TheOddsBookmaker,
    TheOddsEvent,
    TheOddsMarket,
    TheOddsOutcome,
)
from analytis.persistence.orm.odds import OddsSnapshotORM
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


class _FakeAdapter:
    source_id = "the_odds_api"

    def __init__(self, events: list[TheOddsEvent]) -> None:
        self._events = events

    async def fetch_odds(self, **_: object) -> Iterable[TheOddsEvent]:
        return list(self._events)


async def _seed_match(
    factory: async_sessionmaker[AsyncSession],
) -> str:
    async with UnitOfWork(factory) as uow:
        c = Competition(
            name="Odds Test Cup",
            slug="odds-test",
            competition_type=CompetitionType.SELECAO,
            country="INTL",
        )
        await CompetitionRepository(uow.session).upsert(c)
        cstored = await CompetitionRepository(uow.session).get_by_slug("odds-test")
        assert cstored is not None
        s = Season(competition_id=cstored.id, label="2026")
        await SeasonRepository(uow.session).upsert(s)
        sstored = await SeasonRepository(uow.session).get(cstored.id, "2026")
        assert sstored is not None
        for n in ["Brazil", "Morocco"]:
            await TeamRepository(uow.session).upsert(
                Team(
                    name=n, short_name=n[:5].upper(),
                    team_type=TeamType.SELECAO, country="INT",
                )
            )
        bra = await TeamRepository(uow.session).get_by_name("Brazil")
        mar = await TeamRepository(uow.session).get_by_name("Morocco")
        assert bra is not None and mar is not None
        m = Match(
            season_id=sstored.id,
            home_team_id=bra.id,
            away_team_id=mar.id,
            kickoff_utc=datetime(2026, 6, 13, 22, 0, tzinfo=UTC),
            is_home_neutral=True,
            status=MatchStatus.SCHEDULED,
            external_ids={"test": "odds-target"},
        )
        await MatchRepository(uow.session).upsert(m)
    return "odds-target"


@pytest.mark.integration
async def test_ingest_odds_h2h_only(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed_match(session_factory)
    event = TheOddsEvent(
        external_id="ev1",
        sport_key="soccer_fifa_world_cup",
        commence_time=datetime(2026, 6, 13, 22, 0, tzinfo=UTC),
        home_team="Brazil",
        away_team="Morocco",
        bookmakers=[
            TheOddsBookmaker(
                key="pinnacle",
                title="Pinnacle",
                last_update=datetime(2026, 6, 13, 15, 0, tzinfo=UTC),
                markets=[
                    TheOddsMarket(
                        market_key="h2h",
                        outcomes=[
                            TheOddsOutcome(name="Brazil", decimal_odds=2.40),
                            TheOddsOutcome(name="Draw", decimal_odds=3.10),
                            TheOddsOutcome(name="Morocco", decimal_odds=3.20),
                        ],
                    )
                ],
            )
        ],
    )
    adapter = _FakeAdapter([event])
    use_case = IngestOddsUseCase(session_factory, adapter)  # type: ignore[arg-type]
    result = await use_case.execute(IngestOddsParams())
    assert result.records_touched == 3

    async with session_factory() as s:
        n = await s.scalar(select(func.count()).select_from(OddsSnapshotORM))
        assert n == 3

    # Rerun is idempotent
    result2 = await use_case.execute(IngestOddsParams())
    assert result2.records_touched == 0
    async with session_factory() as s:
        n2 = await s.scalar(select(func.count()).select_from(OddsSnapshotORM))
        assert n2 == 3
```

- [ ] **Step 7: Run tests + quality**

```bash
uv run pytest tests/integration/ingestion/test_odds_ingestion.py -v -m integration
uv run mypy src tests
uv run ruff check .
uv run analytis odds --help
```

Expected: 1 integration passes.

- [ ] **Step 8: Stage**

```bash
git add src/analytis/persistence/repositories/odds.py src/analytis/persistence/repositories/__init__.py src/analytis/application/ingest_odds.py src/analytis/cli/odds.py src/analytis/cli/app.py tests/integration/ingestion/test_odds_ingestion.py
```

---

## Task 6: EV math + Kelly fractional stake

**Files:**
- Create: `src/analytis/modeling/ev.py`
- Create: `src/analytis/modeling/kelly.py`
- Test: `tests/unit/modeling/test_ev.py`
- Test: `tests/unit/modeling/test_kelly.py`

- [ ] **Step 1: Write test — `tests/unit/modeling/test_ev.py`**

```python
"""Tests for EV math."""

import pytest

from analytis.modeling.ev import edge, implied_probability, remove_overround


def test_implied_probability() -> None:
    assert implied_probability(2.0) == pytest.approx(0.5)
    assert implied_probability(1.50) == pytest.approx(0.6667, abs=1e-3)


def test_edge_positive_when_model_beats_market() -> None:
    # Model prob 0.55, market odds 2.10 (implied 0.476)
    e = edge(our_prob=0.55, decimal_odds=2.10)
    assert e > 0
    # Edge = our_prob * (odds - 1) - (1 - our_prob)
    expected = 0.55 * 1.10 - 0.45
    assert e == pytest.approx(expected, abs=1e-9)


def test_edge_negative_when_market_beats_model() -> None:
    e = edge(our_prob=0.40, decimal_odds=2.10)
    assert e < 0


def test_remove_overround_h2h() -> None:
    # Market: home 1.85, draw 3.50, away 4.20
    # Implied: 0.541, 0.286, 0.238 -> sum 1.065
    fair = remove_overround([1.85, 3.50, 4.20])
    assert sum(fair) == pytest.approx(1.0, abs=1e-9)
    # Order preserved
    assert fair[0] > fair[1] > fair[2]


def test_remove_overround_two_way() -> None:
    fair = remove_overround([1.91, 1.91])
    assert sum(fair) == pytest.approx(1.0, abs=1e-9)
    assert fair[0] == pytest.approx(0.5)
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/modeling/test_ev.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/analytis/modeling/ev.py`**

```python
"""Expected value math primitives."""


def implied_probability(decimal_odds: float) -> float:
    if decimal_odds < 1.01:
        raise ValueError("decimal_odds must be >= 1.01")
    return 1.0 / decimal_odds


def edge(*, our_prob: float, decimal_odds: float) -> float:
    """Expected unit-stake profit per bet.

    edge = our_prob * (odds - 1) - (1 - our_prob)
    Positive means +EV under our prob.
    """
    if not 0.0 <= our_prob <= 1.0:
        raise ValueError("our_prob must be in [0, 1]")
    if decimal_odds < 1.01:
        raise ValueError("decimal_odds must be >= 1.01")
    return our_prob * (decimal_odds - 1.0) - (1.0 - our_prob)


def remove_overround(decimal_odds_list: list[float]) -> list[float]:
    """Naive proportional overround removal (additive method).
    Returns implied 'fair' probabilities that sum to 1.0.
    """
    if not decimal_odds_list:
        raise ValueError("decimal_odds_list must not be empty")
    implied = [implied_probability(o) for o in decimal_odds_list]
    total = sum(implied)
    if total <= 0:
        raise ValueError("implied probabilities sum to <= 0")
    return [p / total for p in implied]


__all__ = ["edge", "implied_probability", "remove_overround"]
```

- [ ] **Step 4: Write test — `tests/unit/modeling/test_kelly.py`**

```python
"""Tests for fractional Kelly stake."""

import pytest

from analytis.modeling.kelly import kelly_fraction, kelly_stake_units


def test_kelly_zero_edge_is_zero() -> None:
    assert kelly_fraction(our_prob=0.5, decimal_odds=2.0) == pytest.approx(0.0)


def test_kelly_positive_edge() -> None:
    f = kelly_fraction(our_prob=0.55, decimal_odds=2.0)
    # f = (b*p - q) / b where b = odds-1, p=0.55, q=0.45 -> f = (1*0.55 - 0.45)/1 = 0.10
    assert f == pytest.approx(0.10, abs=1e-9)


def test_kelly_negative_capped_at_zero() -> None:
    f = kelly_fraction(our_prob=0.40, decimal_odds=2.0)
    assert f == 0.0


def test_kelly_stake_units_fractional_kelly() -> None:
    # Fractional kelly (1/4) and bankroll 1000 => 25 units expected
    units = kelly_stake_units(
        our_prob=0.55,
        decimal_odds=2.0,
        bankroll=1000.0,
        fraction=0.25,
    )
    # Full kelly = 100 (10% of 1000); 1/4 kelly = 25.
    assert units == pytest.approx(25.0, abs=1e-9)


def test_kelly_stake_units_caps_at_max() -> None:
    units = kelly_stake_units(
        our_prob=0.99,
        decimal_odds=2.0,
        bankroll=1000.0,
        fraction=1.0,
        max_units=20.0,
    )
    assert units == 20.0
```

- [ ] **Step 5: Implement `src/analytis/modeling/kelly.py`**

```python
"""Fractional Kelly criterion stake sizing."""


def kelly_fraction(*, our_prob: float, decimal_odds: float) -> float:
    """Optimal fraction of bankroll for a single bet under Kelly.

    f* = (b*p - q) / b, where b = odds - 1, p = our_prob, q = 1 - p.
    Negative result is clamped to 0 (don't bet).
    """
    if not 0.0 <= our_prob <= 1.0:
        raise ValueError("our_prob must be in [0, 1]")
    if decimal_odds < 1.01:
        raise ValueError("decimal_odds must be >= 1.01")
    b = decimal_odds - 1.0
    p = our_prob
    q = 1.0 - p
    f_star = (b * p - q) / b
    return max(0.0, f_star)


def kelly_stake_units(
    *,
    our_prob: float,
    decimal_odds: float,
    bankroll: float,
    fraction: float = 0.25,
    max_units: float | None = None,
) -> float:
    """Stake in absolute units. Uses *fractional* Kelly to reduce variance.

    fraction=0.25 is the common "quarter Kelly" conservative choice.
    """
    if bankroll <= 0:
        raise ValueError("bankroll must be positive")
    if not 0.0 < fraction <= 1.0:
        raise ValueError("fraction must be in (0, 1]")
    f = kelly_fraction(our_prob=our_prob, decimal_odds=decimal_odds)
    units = bankroll * f * fraction
    if max_units is not None and units > max_units:
        return max_units
    return units


__all__ = ["kelly_fraction", "kelly_stake_units"]
```

- [ ] **Step 6: Run tests + quality**

```bash
uv run pytest tests/unit/modeling/test_ev.py tests/unit/modeling/test_kelly.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 10 tests pass.

- [ ] **Step 7: Stage**

```bash
git add src/analytis/modeling/ev.py src/analytis/modeling/kelly.py tests/unit/modeling/test_ev.py tests/unit/modeling/test_kelly.py
```

---

## Task 7: FindValueBetsUseCase + CLI `analytis bets find-value`

**Files:**
- Create: `src/analytis/persistence/repositories/bets.py`
- Modify: `src/analytis/persistence/repositories/__init__.py`
- Create: `src/analytis/application/find_value_bets.py`
- Create: `src/analytis/cli/bets.py`
- Modify: `src/analytis/cli/app.py`
- Test: `tests/integration/application/test_find_value_bets.py`

- [ ] **Step 1: Create `src/analytis/persistence/repositories/bets.py`**

```python
"""Repository for ValueBet."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.persistence.orm.bets import ValueBetORM


class ValueBetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        match_id: UUID,
        model_version_id: UUID,
        market: str,
        outcome: str,
        bookmaker: str,
        our_prob: float,
        market_prob: float,
        decimal_odds: float,
        edge: float,
        kelly_fraction: float,
        suggested_stake_units: float,
        found_at: datetime,
    ) -> UUID:
        bet_id = uuid4()
        self._session.add(
            ValueBetORM(
                id=bet_id,
                match_id=match_id,
                model_version_id=model_version_id,
                market=market,
                outcome=outcome,
                bookmaker=bookmaker,
                our_prob=our_prob,
                market_prob=market_prob,
                decimal_odds=decimal_odds,
                edge=edge,
                kelly_fraction=kelly_fraction,
                suggested_stake_units=suggested_stake_units,
                found_at=found_at,
            )
        )
        return bet_id

    async def list_for_match(self, match_id: UUID) -> list[ValueBetORM]:
        result = await self._session.scalars(
            select(ValueBetORM).where(ValueBetORM.match_id == match_id)
        )
        return list(result.all())
```

- [ ] **Step 2: Update repositories `__init__.py`**

```python
from analytis.persistence.repositories.bets import ValueBetRepository
```

Add to `__all__`.

- [ ] **Step 3: Create `src/analytis/application/find_value_bets.py`**

```python
"""Use case: find +EV bets by comparing our predictions to bookmaker odds."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.modeling.ev import edge as compute_edge
from analytis.modeling.kelly import kelly_fraction, kelly_stake_units
from analytis.persistence.orm.inference import PredictionORM
from analytis.persistence.repositories import OddsRepository, ValueBetRepository
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class FindValueBetsParams:
    match_id: UUID
    model_version_id: UUID
    min_edge: float = 0.03  # 3% edge threshold
    bankroll: float = 1000.0
    kelly_fraction_value: float = 0.25
    max_units_per_bet: float | None = 50.0


@dataclass
class FindValueBetsResult:
    bets_found: int


class FindValueBetsUseCase:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._factory = session_factory

    async def execute(self, params: FindValueBetsParams) -> FindValueBetsResult:
        async with UnitOfWork(self._factory) as uow:
            preds = (
                await uow.session.scalars(
                    select(PredictionORM).where(
                        PredictionORM.match_id == params.match_id,
                        PredictionORM.model_version_id == params.model_version_id,
                    )
                )
            ).all()
            our_by_outcome: dict[tuple[str, str], PredictionORM] = {
                (p.market, p.outcome): p for p in preds
            }

            odds_repo = OddsRepository(uow.session)
            bets_repo = ValueBetRepository(uow.session)
            now = datetime.now(UTC)

            found = 0
            for market in {p.market for p in preds}:
                latest = await odds_repo.latest_for_match(params.match_id, market)
                # Best odds per outcome across bookmakers
                best_by_outcome: dict[str, tuple[float, str]] = {}
                for q in latest:
                    cur = best_by_outcome.get(q.outcome)
                    if cur is None or q.decimal_odds > cur[0]:
                        best_by_outcome[q.outcome] = (q.decimal_odds, q.bookmaker)

                for outcome, (best_odds, bm) in best_by_outcome.items():
                    pred = our_by_outcome.get((market, outcome))
                    if pred is None:
                        continue
                    our_prob = pred.prob
                    market_prob = 1.0 / best_odds
                    e = compute_edge(our_prob=our_prob, decimal_odds=best_odds)
                    if e < params.min_edge:
                        continue
                    f = kelly_fraction(our_prob=our_prob, decimal_odds=best_odds)
                    units = kelly_stake_units(
                        our_prob=our_prob,
                        decimal_odds=best_odds,
                        bankroll=params.bankroll,
                        fraction=params.kelly_fraction_value,
                        max_units=params.max_units_per_bet,
                    )
                    await bets_repo.insert(
                        match_id=params.match_id,
                        model_version_id=params.model_version_id,
                        market=market,
                        outcome=outcome,
                        bookmaker=bm,
                        our_prob=our_prob,
                        market_prob=market_prob,
                        decimal_odds=best_odds,
                        edge=e,
                        kelly_fraction=f,
                        suggested_stake_units=units,
                        found_at=now,
                    )
                    found += 1
            return FindValueBetsResult(bets_found=found)
```

- [ ] **Step 4: Create `src/analytis/cli/bets.py`**

```python
"""CLI for finding value bets."""

import asyncio
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from analytis.application.find_value_bets import (
    FindValueBetsParams,
    FindValueBetsUseCase,
)
from analytis.config import get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.bets import ValueBetORM
from analytis.persistence.orm.inference import ModelVersionORM

app = typer.Typer(help="Value bet discovery.")
console = Console()


@app.command("find-value")
def find_value(
    match_id: str = typer.Option(..., help="Match UUID."),
    model: str = typer.Option(..., "--model", help="ModelVersion name."),
    min_edge: float = typer.Option(0.03, help="Minimum edge to consider a bet."),
    bankroll: float = typer.Option(1000.0, help="Bankroll size."),
    fraction: float = typer.Option(0.25, help="Kelly fraction (0.25 = quarter)."),
    max_units: float = typer.Option(50.0, help="Max units per bet."),
) -> None:
    """Find +EV bets for a match using current odds."""
    asyncio.run(_find(match_id, model, min_edge, bankroll, fraction, max_units))


async def _find(
    match_id_str: str,
    model_name: str,
    min_edge: float,
    bankroll: float,
    fraction: float,
    max_units: float,
) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as s:
            mv = (
                await s.scalars(
                    select(ModelVersionORM).where(
                        ModelVersionORM.name == model_name
                    )
                )
            ).one_or_none()
            if mv is None:
                console.print(f"[red]Model {model_name!r} not found[/red]")
                raise typer.Exit(code=2)
            mv_id = mv.id

        use_case = FindValueBetsUseCase(factory)
        result = await use_case.execute(
            FindValueBetsParams(
                match_id=UUID(match_id_str),
                model_version_id=mv_id,
                min_edge=min_edge,
                bankroll=bankroll,
                kelly_fraction_value=fraction,
                max_units_per_bet=max_units,
            )
        )
        async with factory() as s:
            bets = (
                await s.scalars(
                    select(ValueBetORM).where(
                        ValueBetORM.match_id == UUID(match_id_str)
                    )
                )
            ).all()

        table = Table(title=f"Value Bets ({mv.name})")
        table.add_column("Market")
        table.add_column("Outcome")
        table.add_column("Book")
        table.add_column("Odds")
        table.add_column("Our %")
        table.add_column("Mkt %")
        table.add_column("Edge")
        table.add_column("Stake (u)")
        for b in bets:
            table.add_row(
                b.market, b.outcome, b.bookmaker,
                f"{b.decimal_odds:.2f}",
                f"{b.our_prob*100:.1f}",
                f"{b.market_prob*100:.1f}",
                f"{b.edge*100:+.1f}%",
                f"{b.suggested_stake_units:.1f}",
            )
        console.print(table)
        console.print(
            f"[green]{result.bets_found} new bets found this run.[/green]"
        )
    finally:
        await engine.dispose()
```

- [ ] **Step 5: Register `bets` in `src/analytis/cli/app.py`**

```python
from analytis.cli import api, backtest, bets, db, ingest, odds, score, train

app.add_typer(bets.app, name="bets", help="Value bet discovery.")
```

- [ ] **Step 6: Integration test — `tests/integration/application/test_find_value_bets.py`**

```python
"""Integration test for FindValueBetsUseCase."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.find_value_bets import (
    FindValueBetsParams,
    FindValueBetsUseCase,
)
from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.persistence.orm.bets import ValueBetORM
from analytis.persistence.orm.inference import (
    FeatureSnapshotORM,
    ModelVersionORM,
    PredictionORM,
)
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    OddsRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


@pytest.mark.integration
async def test_find_value_bets_basic(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # Seed: match + prediction (our prob 0.55) + odds 2.10 (market 0.476) -> edge >0
    async with UnitOfWork(session_factory) as uow:
        c = Competition(
            name="VB Cup", slug="vb-cup",
            competition_type=CompetitionType.SELECAO, country="INTL",
        )
        await CompetitionRepository(uow.session).upsert(c)
        cstored = await CompetitionRepository(uow.session).get_by_slug("vb-cup")
        assert cstored is not None
        s = Season(competition_id=cstored.id, label="2026")
        await SeasonRepository(uow.session).upsert(s)
        sstored = await SeasonRepository(uow.session).get(cstored.id, "2026")
        assert sstored is not None
        for n in ["Team-A", "Team-B"]:
            await TeamRepository(uow.session).upsert(
                Team(
                    name=n, short_name=n[:5].upper(),
                    team_type=TeamType.SELECAO, country="INT",
                )
            )
        a = await TeamRepository(uow.session).get_by_name("Team-A")
        b = await TeamRepository(uow.session).get_by_name("Team-B")
        assert a is not None and b is not None
        match = Match(
            season_id=sstored.id,
            home_team_id=a.id, away_team_id=b.id,
            kickoff_utc=datetime(2026, 7, 1, 18, tzinfo=UTC),
            is_home_neutral=True,
            status=MatchStatus.SCHEDULED,
            external_ids={"test": "vb"},
        )
        await MatchRepository(uow.session).upsert(match)
        stored_match = await MatchRepository(uow.session).get_by_external_id(
            "test", "vb"
        )
        assert stored_match is not None

        # Insert model_version + prediction
        mv_id = uuid4()
        uow.session.add(
            ModelVersionORM(
                id=mv_id, name="vb-mv", family="dixon-coles",
                git_sha="sha", hyperparams={}, metrics={}, is_promoted=False,
            )
        )
        snap_id = uuid4()
        snap_at = datetime(2026, 6, 30, tzinfo=UTC)
        uow.session.add(
            FeatureSnapshotORM(
                id=snap_id,
                match_id=stored_match.id,
                snapshot_taken_at=snap_at,
                features={},
                created_at=snap_at,
            )
        )
        await uow.session.flush()
        uow.session.add(
            PredictionORM(
                id=uuid4(),
                match_id=stored_match.id,
                market="1x2",
                outcome="home",
                prob=0.55,
                ci_low=0.50,
                ci_high=0.60,
                model_version_id=mv_id,
                feature_snapshot_id=snap_id,
                created_at=snap_at,
            )
        )
        # Inserir odds
        await OddsRepository(uow.session).insert_quote(
            match_id=stored_match.id,
            bookmaker="pinnacle",
            market="1x2",
            outcome="home",
            decimal_odds=2.10,
            snapshot_taken_at=snap_at,
        )

    use_case = FindValueBetsUseCase(session_factory)
    result = await use_case.execute(
        FindValueBetsParams(
            match_id=stored_match.id,
            model_version_id=mv_id,
            min_edge=0.01,
            bankroll=1000.0,
            kelly_fraction_value=0.25,
        )
    )
    assert result.bets_found == 1

    async with session_factory() as s:
        bets = (
            await s.scalars(
                select(ValueBetORM).where(
                    ValueBetORM.match_id == stored_match.id
                )
            )
        ).all()
        assert len(bets) == 1
        bet = bets[0]
        assert bet.outcome == "home"
        assert bet.decimal_odds == pytest.approx(2.10)
        assert bet.suggested_stake_units > 0
```

- [ ] **Step 7: Run tests + quality**

```bash
uv run pytest tests/integration/application/test_find_value_bets.py -v -m integration
uv run mypy src tests
uv run ruff check .
```

Expected: 1 test passes.

- [ ] **Step 8: Stage**

```bash
git add src/analytis/persistence/repositories/bets.py src/analytis/persistence/repositories/__init__.py src/analytis/application/find_value_bets.py src/analytis/cli/bets.py src/analytis/cli/app.py tests/integration/application/test_find_value_bets.py
```

---

## Task 8: Bootstrap CI for Dixon-Coles params

**Files:**
- Create: `src/analytis/modeling/bootstrap.py`
- Test: `tests/unit/modeling/test_bootstrap.py`

- [ ] **Step 1: Write test FIRST**

```python
"""Tests for bootstrap CI of Dixon-Coles fits."""

import math
import random
from datetime import UTC, datetime

import pytest

from analytis.modeling.bootstrap import (
    BootstrapResult,
    bootstrap_fit,
    market_ci_from_samples,
)
from analytis.modeling.fitting import MatchObservation


def _synth_matches(n_teams: int = 4, n_rounds: int = 8, seed: int = 1) -> list[MatchObservation]:
    rng = random.Random(seed)
    teams = [f"T{i}" for i in range(n_teams)]
    obs: list[MatchObservation] = []
    day = 0
    for _ in range(n_rounds):
        for i, h in enumerate(teams):
            for j, a in enumerate(teams):
                if i == j:
                    continue
                obs.append(
                    MatchObservation(
                        home_team=h, away_team=a,
                        home_goals=rng.randint(0, 3),
                        away_goals=rng.randint(0, 3),
                        kickoff_utc=datetime(2024, 1, 1, tzinfo=UTC),
                        is_neutral=False,
                    )
                )
                day += 1
    return obs


def test_bootstrap_returns_n_samples() -> None:
    matches = _synth_matches()
    result = bootstrap_fit(matches, n_samples=5, max_iter=50, seed=42)
    assert isinstance(result, BootstrapResult)
    assert len(result.samples) == 5
    assert all("T0" in s.attack for s in result.samples)


def test_market_ci_from_samples_brackets_point_estimate() -> None:
    matches = _synth_matches()
    result = bootstrap_fit(matches, n_samples=20, max_iter=50, seed=1)
    # Pick a known team pair
    home, away = "T0", "T1"
    point, low, high = market_ci_from_samples(
        result.samples, home_team=home, away_team=away,
        market="1x2", outcome="home", is_neutral=False,
    )
    assert 0.0 <= low <= point <= high <= 1.0
    # Brackets should have positive width
    assert high - low > 1e-3


def test_market_ci_known_team_missing_raises() -> None:
    matches = _synth_matches()
    result = bootstrap_fit(matches, n_samples=5, max_iter=50, seed=2)
    with pytest.raises(KeyError):
        market_ci_from_samples(
            result.samples, home_team="UNKNOWN", away_team="T0",
            market="1x2", outcome="home", is_neutral=False,
        )
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/modeling/test_bootstrap.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/analytis/modeling/bootstrap.py`**

```python
"""Bootstrap resampling for Dixon-Coles parameter uncertainty.

For each bootstrap sample, draw N matches with replacement from the input
list and refit. Use the spread of per-match market probabilities across
samples as a credible interval.
"""

import math
import random
from dataclasses import dataclass

import numpy as np

from analytis.modeling.dixon_coles import score_matrix
from analytis.modeling.fitting import (
    DixonColesParams,
    FitConfig,
    MatchObservation,
    fit_dixon_coles,
)
from analytis.modeling.markets import (
    btts_probabilities,
    match_result_probabilities,
    over_under_probabilities,
)


@dataclass
class BootstrapResult:
    samples: list[DixonColesParams]


def bootstrap_fit(
    matches: list[MatchObservation],
    *,
    n_samples: int = 50,
    max_iter: int = 200,
    decay_per_day: float = 0.0,
    seed: int | None = None,
) -> BootstrapResult:
    if n_samples <= 0:
        raise ValueError("n_samples must be positive")
    rng = random.Random(seed)
    samples: list[DixonColesParams] = []
    n = len(matches)
    for _ in range(n_samples):
        drawn = [matches[rng.randrange(n)] for _ in range(n)]
        try:
            fit = fit_dixon_coles(
                drawn,
                config=FitConfig(max_iter=max_iter, decay_per_day=decay_per_day),
            )
            samples.append(fit)
        except ValueError:
            continue
    return BootstrapResult(samples=samples)


def _market_prob_for_sample(
    params: DixonColesParams,
    home_team: str,
    away_team: str,
    market: str,
    outcome: str,
    is_neutral: bool,
) -> float:
    if home_team not in params.attack:
        raise KeyError(f"{home_team} missing in sample")
    if away_team not in params.attack:
        raise KeyError(f"{away_team} missing in sample")
    ha = 0.0 if is_neutral else params.home_advantage
    lam_h = math.exp(params.attack[home_team] - params.defense[away_team] + ha)
    lam_a = math.exp(params.attack[away_team] - params.defense[home_team])
    matrix = score_matrix(lam_h, lam_a, params.rho, max_goals=10)
    if market == "1x2":
        mr = match_result_probabilities(matrix)
        return {"home": mr.home, "draw": mr.draw, "away": mr.away}[outcome]
    if market == "over_under_goals":
        ou = over_under_probabilities(matrix, line=2.5)
        return ou.over if outcome.startswith("over") else ou.under
    if market == "btts":
        bt = btts_probabilities(matrix)
        return bt.yes if outcome == "yes" else bt.no
    raise ValueError(f"unknown market {market!r}")


def market_ci_from_samples(
    samples: list[DixonColesParams],
    *,
    home_team: str,
    away_team: str,
    market: str,
    outcome: str,
    is_neutral: bool,
    ci_level: float = 0.95,
) -> tuple[float, float, float]:
    """Returns (point_estimate, ci_low, ci_high) using percentiles."""
    if not samples:
        raise ValueError("samples must not be empty")
    probs = [
        _market_prob_for_sample(
            s, home_team, away_team, market, outcome, is_neutral
        )
        for s in samples
    ]
    arr = np.array(probs, dtype=np.float64)
    point = float(arr.mean())
    lower_q = (1.0 - ci_level) / 2.0 * 100.0
    upper_q = 100.0 - lower_q
    low = float(np.percentile(arr, lower_q))
    high = float(np.percentile(arr, upper_q))
    return point, low, high


__all__ = [
    "BootstrapResult",
    "bootstrap_fit",
    "market_ci_from_samples",
]
```

- [ ] **Step 4: Run tests + quality**

```bash
uv run pytest tests/unit/modeling/test_bootstrap.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 3 tests pass (bootstrap may take ~10-20s).

- [ ] **Step 5: Stage**

```bash
git add src/analytis/modeling/bootstrap.py tests/unit/modeling/test_bootstrap.py
```

---

## Task 9: Isotonic calibration per market

**Files:**
- Create: `src/analytis/modeling/isotonic.py`
- Test: `tests/unit/modeling/test_isotonic.py`

- [ ] **Step 1: Write test FIRST**

```python
"""Tests for isotonic calibration."""

import numpy as np
import pytest

from analytis.modeling.isotonic import IsotonicCalibrator


def test_calibrator_fit_transform_identity() -> None:
    cal = IsotonicCalibrator()
    probs = [0.1, 0.3, 0.5, 0.7, 0.9]
    outcomes = [0, 0, 1, 1, 1]
    cal.fit(probs=probs, outcomes=outcomes)
    calibrated = [cal.predict(p) for p in probs]
    # Output is monotone non-decreasing
    for a, b in zip(calibrated, calibrated[1:], strict=True):
        assert a <= b


def test_calibrator_corrects_overconfidence() -> None:
    rng = np.random.default_rng(42)
    n = 500
    raw = rng.uniform(0, 1, size=n)
    # Generate outcomes where the true probability is 0.5 * raw (overconfident)
    true_prob = 0.5 * raw
    outcomes = (rng.uniform(0, 1, size=n) < true_prob).astype(int).tolist()

    cal = IsotonicCalibrator()
    cal.fit(probs=raw.tolist(), outcomes=outcomes)
    # After calibration, mid-range raw probs should land closer to 0.5*raw
    sample = 0.8
    out = cal.predict(sample)
    assert out < sample  # was overconfident at 0.8, calibrated lower
    assert 0.0 <= out <= 1.0


def test_calibrator_predict_without_fit_raises() -> None:
    cal = IsotonicCalibrator()
    with pytest.raises(RuntimeError, match="not fitted"):
        cal.predict(0.5)
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/modeling/test_isotonic.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/analytis/modeling/isotonic.py`**

```python
"""Isotonic regression calibration wrapper around scikit-learn."""

from typing import cast

import numpy as np
from sklearn.isotonic import IsotonicRegression


class IsotonicCalibrator:
    def __init__(self, *, out_of_bounds: str = "clip") -> None:
        self._model: IsotonicRegression | None = None
        self._out_of_bounds = out_of_bounds

    def fit(self, *, probs: list[float], outcomes: list[int]) -> None:
        if len(probs) != len(outcomes):
            raise ValueError("probs and outcomes must have same length")
        x = np.array(probs, dtype=np.float64)
        y = np.array(outcomes, dtype=np.float64)
        model = IsotonicRegression(
            y_min=0.0, y_max=1.0,
            increasing=True,
            out_of_bounds=self._out_of_bounds,
        )
        model.fit(x, y)
        self._model = model

    def predict(self, prob: float) -> float:
        if self._model is None:
            raise RuntimeError("IsotonicCalibrator not fitted")
        arr = np.array([prob], dtype=np.float64)
        out = self._model.predict(arr)
        return float(cast(np.ndarray, out)[0])


__all__ = ["IsotonicCalibrator"]
```

- [ ] **Step 4: Run tests + quality**

```bash
uv run pytest tests/unit/modeling/test_isotonic.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 3 tests pass.

- [ ] **Step 5: Stage**

```bash
git add src/analytis/modeling/isotonic.py tests/unit/modeling/test_isotonic.py
```

---

## Task 10: TrackCLVUseCase + CLI

**Files:**
- Create: `src/analytis/application/track_clv.py`
- Modify: `src/analytis/cli/bets.py` (add `track-clv` subcommand)
- Test: `tests/integration/application/test_track_clv.py`

CLV = log(odds_when_we_bet / closing_odds). Positive = our odds were better than the line moved to (skill signal).

- [ ] **Step 1: Write integration test FIRST**

```python
"""Integration test for CLV tracking."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.track_clv import TrackCLVParams, TrackCLVUseCase
from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.persistence.orm.bets import ValueBetORM
from analytis.persistence.orm.inference import ModelVersionORM
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    OddsRepository,
    SeasonRepository,
    TeamRepository,
    ValueBetRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


@pytest.mark.integration
async def test_track_clv_updates_bet(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with UnitOfWork(session_factory) as uow:
        c = Competition(
            name="CLV Cup", slug="clv-cup",
            competition_type=CompetitionType.SELECAO, country="INTL",
        )
        await CompetitionRepository(uow.session).upsert(c)
        cstored = await CompetitionRepository(uow.session).get_by_slug("clv-cup")
        assert cstored is not None
        s = Season(competition_id=cstored.id, label="2026")
        await SeasonRepository(uow.session).upsert(s)
        sstored = await SeasonRepository(uow.session).get(cstored.id, "2026")
        assert sstored is not None
        for n in ["X", "Y"]:
            await TeamRepository(uow.session).upsert(
                Team(
                    name=n, short_name=n,
                    team_type=TeamType.SELECAO, country="INT",
                )
            )
        x = await TeamRepository(uow.session).get_by_name("X")
        y = await TeamRepository(uow.session).get_by_name("Y")
        assert x is not None and y is not None
        match = Match(
            season_id=sstored.id,
            home_team_id=x.id, away_team_id=y.id,
            kickoff_utc=datetime(2026, 7, 1, 18, tzinfo=UTC),
            is_home_neutral=True,
            status=MatchStatus.SCHEDULED,
            external_ids={"test": "clv"},
        )
        await MatchRepository(uow.session).upsert(match)
        stored_match = await MatchRepository(uow.session).get_by_external_id(
            "test", "clv"
        )
        assert stored_match is not None

        mv_id = uuid4()
        uow.session.add(
            ModelVersionORM(
                id=mv_id, name="clv-mv", family="dixon-coles",
                git_sha="sha", hyperparams={}, metrics={}, is_promoted=False,
            )
        )
        # 1. Insert a value bet (we took 2.50 on home)
        bet_id = await ValueBetRepository(uow.session).insert(
            match_id=stored_match.id,
            model_version_id=mv_id,
            market="1x2",
            outcome="home",
            bookmaker="pinnacle",
            our_prob=0.50,
            market_prob=0.40,
            decimal_odds=2.50,
            edge=0.05,
            kelly_fraction=0.05,
            suggested_stake_units=10.0,
            found_at=datetime(2026, 6, 25, tzinfo=UTC),
        )
        # 2. Insert closing odds (closer to kickoff): 2.20 (line moved with us)
        await OddsRepository(uow.session).insert_quote(
            match_id=stored_match.id,
            bookmaker="pinnacle",
            market="1x2",
            outcome="home",
            decimal_odds=2.20,
            snapshot_taken_at=datetime(2026, 7, 1, 17, 45, tzinfo=UTC),
        )

    use_case = TrackCLVUseCase(session_factory)
    result = await use_case.execute(TrackCLVParams(match_id=stored_match.id))
    assert result.bets_updated == 1

    async with session_factory() as s:
        bet = (
            await s.scalars(select(ValueBetORM).where(ValueBetORM.id == bet_id))
        ).one()
        assert bet.closing_decimal_odds == pytest.approx(2.20)
        # CLV is positive because we got 2.50 and line closed at 2.20
        assert bet.closing_clv is not None
        assert bet.closing_clv > 0
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/integration/application/test_track_clv.py -v -m integration
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/analytis/application/track_clv.py`**

```python
"""Use case: update CLV (closing-line value) on ValueBet rows."""

import math
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.persistence.orm.bets import ValueBetORM
from analytis.persistence.repositories import OddsRepository
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class TrackCLVParams:
    match_id: UUID


@dataclass
class TrackCLVResult:
    bets_updated: int


class TrackCLVUseCase:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._factory = session_factory

    async def execute(self, params: TrackCLVParams) -> TrackCLVResult:
        async with UnitOfWork(self._factory) as uow:
            bets = (
                await uow.session.scalars(
                    select(ValueBetORM).where(
                        ValueBetORM.match_id == params.match_id
                    )
                )
            ).all()
            odds_repo = OddsRepository(uow.session)
            updated = 0
            for bet in bets:
                latest = await odds_repo.latest_for_match(
                    params.match_id, bet.market
                )
                same = [
                    q for q in latest
                    if q.bookmaker == bet.bookmaker and q.outcome == bet.outcome
                ]
                if not same:
                    continue
                closing = max(same, key=lambda q: q.snapshot_taken_at)
                if closing.snapshot_taken_at <= bet.found_at:
                    continue
                bet.closing_decimal_odds = closing.decimal_odds
                bet.closing_clv = math.log(bet.decimal_odds / closing.decimal_odds)
                updated += 1
            return TrackCLVResult(bets_updated=updated)
```

- [ ] **Step 4: Add CLI command to `src/analytis/cli/bets.py`**

Append:

```python
from analytis.application.track_clv import TrackCLVParams, TrackCLVUseCase


@app.command("track-clv")
def track_clv(
    match_id: str = typer.Option(..., help="Match UUID."),
) -> None:
    """Update CLV on existing value bets using current closing odds."""
    asyncio.run(_track_clv(match_id))


async def _track_clv(match_id_str: str) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        use_case = TrackCLVUseCase(factory)
        result = await use_case.execute(
            TrackCLVParams(match_id=UUID(match_id_str))
        )
        console.print(
            f"[green]Updated CLV on {result.bets_updated} bets.[/green]"
        )
    finally:
        await engine.dispose()
```

- [ ] **Step 5: Run tests + quality**

```bash
uv run pytest tests/integration/application/test_track_clv.py -v -m integration
uv run mypy src tests
uv run ruff check .
```

Expected: 1 test passes.

- [ ] **Step 6: Stage**

```bash
git add src/analytis/application/track_clv.py src/analytis/cli/bets.py tests/integration/application/test_track_clv.py
```

---

## Task 11 onwards (overview — detail when reaching)

The remaining tasks are decomposed at the same granularity. Each will get a full code-complete spec when reached.

### Task 11: XGBoost classifier (1X2 / OU / BTTS) over feature vectors

Wrap `xgboost.XGBClassifier` with our feature dict → vector transform. Output: per-outcome prob arrays. Unit test: classifier trained on synthetic features recovers the true mapping above chance.

### Task 12: XGBoost regressor for lambda_home / lambda_away

Two regressors (one per side) trained on snapshots × historical (home_goals, away_goals). Convert outputs to Poisson lambdas. Unit test: regressor recovers known lambda mapping on synthetic data.

### Task 13: Stacking ensemble — logistic meta-model

Combines DC + XGBoost classifier probabilities into final per-market probability via `sklearn.linear_model.LogisticRegression`. Trained on walk-forward out-of-fold predictions. Output: `Ensemble` object with `.predict(market, features) -> prob`.

### Task 14: Corners model (Poisson bivariate)

**Open question:** free dataset for corners history? If yes, mirror Dixon-Coles structure trained on (home_corners, away_corners). If no data available within ~2 hours of investigation, document the gap and skip the market. Acceptance: either model trains + derives over/under 9.5 corners probabilities, or `corners` is excluded from `find-value` and noted in README.

### Task 15: TrainXGBoostUseCase + CLI `analytis train xgboost`

Loads finished matches → builds feature snapshots (reuses Plan 2 builder) → trains XGBoost models → persists via ModelVersion ORM (family="xgboost") with metrics block including Brier per market.

### Task 16: API routes — /v1/odds, /v1/value-bets

`GET /v1/matches/{id}/odds` returns latest odds grouped by market+outcome with the best book per outcome.
`GET /v1/matches/{id}/value-bets` returns ValueBet rows.
`GET /v1/bets/clv-summary` returns aggregate CLV stats by model.

### Task 17: README update + acceptance criteria run

Update README with new commands and end-to-end workflow including: `odds fetch` → `bets find-value` → place bets externally → `bets track-clv` post-game. Then run the acceptance checklist.

---

## Acceptance Criteria (end-of-plan checklist)

- [ ] `analytis odds fetch` ingests odds for at least 5 bookmakers per Copa 2026 match.
- [ ] `analytis bets find-value --match <id> --model dc-wc-v0.2.0-no-decay` returns >=1 +EV bet on at least 5 different matches (otherwise model is not finding edge — flag as concern).
- [ ] All ValueBet rows persisted have `kelly_fraction >= 0`, `suggested_stake_units <= max_units`, `edge >= min_edge`.
- [ ] After running `bets track-clv` on a completed match, `closing_clv` is non-null on at least one bet (proves the wiring works; sign depends on line movement).
- [ ] Bootstrap CIs replace the simplistic Wilson CIs in `prediction.ci_low`/`ci_high`. Verify via inspection that CIs widen for low-data teams.
- [ ] XGBoost ensemble Brier on 1X2 home is lower than pure DC Brier on the same walk-forward CV slices (or, if not, the deviation is documented).
- [ ] `GET /v1/matches/{id}/value-bets` returns the same data as the CLI.
- [ ] Full test suite green (`uv run pytest`); mypy strict + ruff clean.

If any item fails, add a follow-up task before declaring the plan done.
