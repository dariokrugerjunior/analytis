# Plano 2 — Features + Dixon-Coles

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingerir histórico internacional gratuito (~45k jogos desde 1872), calcular ELO mundial localmente, construir catálogo de features reprodutíveis, treinar Dixon-Coles com shrinkage bayesiano por confederação, validar via walk-forward CV sobre Copas 2018/2022, e gerar primeiras previsões 1X2/Over-Under-2.5/BTTS imutáveis em `prediction` table com intervalo de credibilidade.

**Architecture:** Adapter pluggable novo para CSV histórico de jogos internacionais (martj42/international_results). ELO calculado em Python sobre nosso banco (não scraping). Camada `features/` com registry de funções puras `f(match_id, as_of) -> value`, snapshots imutáveis em `feature_snapshot`. Camada `modeling/` com Dixon-Coles fitter (L-BFGS via scipy), correção de placares baixos, decaimento temporal, prior bayesiano por confederação FIFA. Walk-forward CV sobre Copas históricas. Scoring pipeline grava em `prediction` com `ci_low`/`ci_high` por bootstrap.

**Tech Stack:** Existente (Python 3.12, uv, Ruff, Mypy strict, Pytest, FastAPI, SQLAlchemy 2.x async, Pydantic 2, Alembic, Typer, httpx, structlog) + **novos**: numpy, scipy, pandas (treino/scoring), pyarrow (cache de features em parquet).

**Branch:** trabalhar direto em `main` (preferência do usuário — sem feature branches).

**Spec:** `docs/superpowers/specs/2026-06-12-football-analytics-design.md` §6 (features) + §7 (modelagem) + §11 sem 3-4.

---

## Estrutura de arquivos do plano

```
analytis/
├── migrations/versions/
│   └── 0002_elo_history_and_confederations.py     # nova migration
├── src/analytis/
│   ├── domain/
│   │   ├── confederation.py                       # FIFA continental + helpers
│   │   └── elo.py                                 # EloRating entity
│   ├── persistence/orm/
│   │   ├── elo.py                                 # EloHistoryORM
│   │   └── catalog.py                             # +confederation column
│   ├── persistence/repositories/
│   │   ├── elo.py                                 # EloHistoryRepository
│   │   └── feature_snapshot.py                    # SnapshotRepository
│   ├── ingestion/adapters/
│   │   └── international_results.py               # CSV adapter
│   ├── application/
│   │   ├── ingest_international_history.py        # use case
│   │   ├── build_features.py                      # use case
│   │   ├── train_dixon_coles.py                   # use case
│   │   ├── score_match.py                         # use case
│   │   └── backtest.py                            # walk-forward CV
│   ├── features/
│   │   ├── __init__.py
│   │   ├── registry.py                            # FeatureFn protocol + registry
│   │   ├── elo.py                                 # ELO calc + features
│   │   ├── strength.py                            # attack/defense w/ shrinkage
│   │   ├── form.py                                # rolling windows + decay
│   │   ├── context.py                             # rest, neutral, stage, H2H
│   │   └── builder.py                             # vector builder
│   ├── modeling/
│   │   ├── __init__.py
│   │   ├── dixon_coles.py                         # math core
│   │   ├── fitting.py                             # L-BFGS fitter
│   │   ├── markets.py                             # 1X2/OU2.5/BTTS derivations
│   │   ├── confederation_prior.py                 # bayesian shrinkage
│   │   ├── evaluation.py                          # Brier, log-loss, ECE
│   │   ├── walk_forward.py                        # CV
│   │   └── persistence.py                         # save/load fitted model
│   ├── scoring/
│   │   ├── __init__.py
│   │   └── pipeline.py                            # scoring orchestration
│   ├── cli/
│   │   ├── ingest.py                              # +history subcommand
│   │   ├── features.py                            # new subcommands
│   │   ├── train.py                               # new subcommands
│   │   ├── score.py                               # new subcommands
│   │   └── backtest.py                            # new subcommand
│   └── api/routes/
│       ├── predictions.py                         # new routes
│       └── models.py                              # new routes
└── tests/
    ├── unit/
    │   ├── features/test_elo_math.py
    │   ├── features/test_strength_shrinkage.py
    │   ├── features/test_form.py
    │   ├── features/test_context.py
    │   ├── modeling/test_dixon_coles_math.py
    │   ├── modeling/test_markets.py
    │   ├── modeling/test_confederation_prior.py
    │   └── modeling/test_evaluation.py
    └── integration/
        ├── ingestion/test_international_history.py
        ├── application/test_build_features.py
        ├── application/test_train_dixon_coles.py
        ├── application/test_score_match.py
        ├── application/test_backtest.py
        └── api/test_predictions.py
```

---

## Convenções (válidas em todas as tasks)

- Python 3.12+; sem `from __future__ import annotations`.
- TDD obrigatório em código de domínio, features e modeling. Não-TDD apenas para migrations Alembic e wiring CLI/API.
- Commits frequentes, isolados por task. Mensagens em inglês `<type>: <message>`.
- **NÃO** adicionar trailer `Co-Authored-By: Claude...`.
- uv path: `C:\Users\PC Gamer\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe` — prefix em todo Bash:
  ```bash
  export PATH="/c/Users/PC Gamer/AppData/Local/Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe:$PATH"
  ```
- env vars necessárias (Postgres na porta 5434, herdadas do Plano 1):
  ```bash
  export ANALYTIS_DATABASE_URL="postgresql+psycopg://analytis:analytis_dev@localhost:5434/analytis"
  export ANALYTIS_API_KEY="local-dev"
  ```
- Postgres já tem 72 jogos da Copa 2026 do Plano 1.

---

## Task 1: Adicionar dependências numéricas

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Confirmar que está em `main`**

```bash
cd "C:\Projetos\Pessoal\analytis"
git branch --show-current  # expected: main
```

- [ ] **Step 2: Adicionar dependências numéricas em `pyproject.toml`**

Localize a lista `dependencies = [...]` e adicione (em ordem alfabética):

```toml
    "numpy>=2.1.0",
    "pandas>=2.2.3",
    "pyarrow>=18.0.0",
    "scipy>=1.14.1",
```

- [ ] **Step 3: Sincronizar**

```bash
export PATH="/c/Users/PC Gamer/AppData/Local/Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe:$PATH"
uv sync
uv run python -c "import numpy, pandas, scipy, pyarrow; print('ok')"
```

Expected: prints "ok".

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add numpy, scipy, pandas, pyarrow for modeling"
```

---

## Task 2: Domain entity Confederation + helpers

**Files:**
- Create: `src/analytis/domain/confederation.py`
- Test: `tests/unit/domain/test_confederation.py`

- [ ] **Step 1: Write the failing test — `tests/unit/domain/test_confederation.py`**

```python
"""Tests for FIFA confederation enum and helpers."""

import pytest

from analytis.domain.confederation import Confederation, confederation_of_country


def test_known_country_maps_to_confederation() -> None:
    assert confederation_of_country("BRA") is Confederation.CONMEBOL
    assert confederation_of_country("FRA") is Confederation.UEFA
    assert confederation_of_country("MEX") is Confederation.CONCACAF
    assert confederation_of_country("JPN") is Confederation.AFC
    assert confederation_of_country("MAR") is Confederation.CAF
    assert confederation_of_country("AUS") is Confederation.AFC  # since 2006
    assert confederation_of_country("NZL") is Confederation.OFC


def test_unknown_country_returns_unknown() -> None:
    assert confederation_of_country("ZZZ") is Confederation.UNKNOWN


def test_case_insensitive() -> None:
    assert confederation_of_country("bra") is Confederation.CONMEBOL


def test_all_confederation_codes_are_short() -> None:
    for c in Confederation:
        assert len(c.value) <= 10
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/domain/test_confederation.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/analytis/domain/confederation.py`**

```python
"""FIFA continental confederation classification."""

from enum import StrEnum


class Confederation(StrEnum):
    UEFA = "UEFA"
    CONMEBOL = "CONMEBOL"
    CONCACAF = "CONCACAF"
    AFC = "AFC"
    CAF = "CAF"
    OFC = "OFC"
    UNKNOWN = "UNKNOWN"


_COUNTRY_TO_CONFED: dict[str, Confederation] = {
    # CONMEBOL (10)
    "ARG": Confederation.CONMEBOL, "BOL": Confederation.CONMEBOL,
    "BRA": Confederation.CONMEBOL, "CHI": Confederation.CONMEBOL,
    "COL": Confederation.CONMEBOL, "ECU": Confederation.CONMEBOL,
    "PAR": Confederation.CONMEBOL, "PER": Confederation.CONMEBOL,
    "URU": Confederation.CONMEBOL, "VEN": Confederation.CONMEBOL,
    # CONCACAF (selected — 35 members total; we include the ones likely to play)
    "MEX": Confederation.CONCACAF, "USA": Confederation.CONCACAF,
    "CAN": Confederation.CONCACAF, "CRC": Confederation.CONCACAF,
    "HON": Confederation.CONCACAF, "PAN": Confederation.CONCACAF,
    "JAM": Confederation.CONCACAF, "HAI": Confederation.CONCACAF,
    "SLV": Confederation.CONCACAF, "TRI": Confederation.CONCACAF,
    # CAF (selected — 54 members)
    "MAR": Confederation.CAF, "SEN": Confederation.CAF,
    "EGY": Confederation.CAF, "NGA": Confederation.CAF,
    "CMR": Confederation.CAF, "GHA": Confederation.CAF,
    "TUN": Confederation.CAF, "ALG": Confederation.CAF,
    "RSA": Confederation.CAF, "CIV": Confederation.CAF,
    "MLI": Confederation.CAF,
    # AFC (selected — 47 members; Australia joined 2006)
    "JPN": Confederation.AFC, "KOR": Confederation.AFC,
    "AUS": Confederation.AFC, "IRN": Confederation.AFC,
    "KSA": Confederation.AFC, "QAT": Confederation.AFC,
    "UAE": Confederation.AFC, "IRQ": Confederation.AFC,
    "UZB": Confederation.AFC, "CHN": Confederation.AFC,
    # OFC (Oceania)
    "NZL": Confederation.OFC, "FIJ": Confederation.OFC,
    "SOL": Confederation.OFC, "VAN": Confederation.OFC,
    # UEFA (selected — 55 members)
    "FRA": Confederation.UEFA, "GER": Confederation.UEFA,
    "ESP": Confederation.UEFA, "ITA": Confederation.UEFA,
    "ENG": Confederation.UEFA, "POR": Confederation.UEFA,
    "NED": Confederation.UEFA, "BEL": Confederation.UEFA,
    "CRO": Confederation.UEFA, "POL": Confederation.UEFA,
    "DEN": Confederation.UEFA, "SUI": Confederation.UEFA,
    "AUT": Confederation.UEFA, "SWE": Confederation.UEFA,
    "NOR": Confederation.UEFA, "CZE": Confederation.UEFA,
    "TUR": Confederation.UEFA, "SCO": Confederation.UEFA,
    "WAL": Confederation.UEFA, "SRB": Confederation.UEFA,
    "UKR": Confederation.UEFA, "RUS": Confederation.UEFA,
    "GRE": Confederation.UEFA, "ROU": Confederation.UEFA,
    "HUN": Confederation.UEFA, "BIH": Confederation.UEFA,
    "BOS": Confederation.UEFA, "ISL": Confederation.UEFA,
    "FIN": Confederation.UEFA, "IRL": Confederation.UEFA,
    "NIR": Confederation.UEFA, "ALB": Confederation.UEFA,
    "SVK": Confederation.UEFA, "SVN": Confederation.UEFA,
    "BUL": Confederation.UEFA,
}


def confederation_of_country(country_code: str) -> Confederation:
    """Map ISO-3 country code to FIFA confederation."""
    return _COUNTRY_TO_CONFED.get(country_code.upper(), Confederation.UNKNOWN)


__all__ = ["Confederation", "confederation_of_country"]
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/unit/domain/test_confederation.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 4 tests pass, mypy + ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/analytis/domain/confederation.py tests/unit/domain/test_confederation.py
git commit -m "feat(domain): add FIFA confederation enum and country mapping"
```

---

## Task 3: Domain entity EloRating + ORM + migration

**Files:**
- Create: `src/analytis/domain/elo.py`
- Create: `src/analytis/persistence/orm/elo.py`
- Modify: `src/analytis/persistence/orm/__init__.py`
- Modify: `src/analytis/persistence/orm/catalog.py` (add confederation column)
- Test: `tests/unit/domain/test_elo.py`

- [ ] **Step 1: Write test — `tests/unit/domain/test_elo.py`**

```python
"""Tests for EloRating domain entity."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from analytis.domain.elo import EloRating


def test_elo_rating_minimal() -> None:
    r = EloRating(
        team_id=uuid4(),
        rating=1500.0,
        as_of=datetime(2026, 6, 12, tzinfo=UTC),
    )
    assert r.rating == 1500.0


def test_elo_rating_rejects_naive() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        EloRating(team_id=uuid4(), rating=1500.0, as_of=datetime(2026, 6, 12))


def test_elo_rating_rejects_negative() -> None:
    with pytest.raises(ValueError):
        EloRating(
            team_id=uuid4(), rating=-100.0,
            as_of=datetime(2026, 6, 12, tzinfo=UTC),
        )
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/domain/test_elo.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/analytis/domain/elo.py`**

```python
"""ELO rating domain entity (one rating value at a point in time)."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from analytis.domain.ids import TeamId


class EloRating(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: TeamId = Field(default_factory=uuid4)
    team_id: TeamId
    rating: float = Field(ge=0.0, le=4000.0)
    as_of: datetime
    games_played: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate(self) -> "EloRating":
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return self
```

- [ ] **Step 4: Add `confederation` column to `TeamORM`**

In `src/analytis/persistence/orm/catalog.py`, locate `class TeamORM` and add column right after `country`:

```python
    confederation: Mapped[str | None] = mapped_column(String(20), nullable=True)
```

- [ ] **Step 5: Create `src/analytis/persistence/orm/elo.py`**

```python
"""ORM model for ELO rating history."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from analytis.persistence.orm.base import Base, TimestampMixin


class EloHistoryORM(Base, TimestampMixin):
    __tablename__ = "elo_history"
    __table_args__ = (
        Index("ix_elo_history_team_as_of", "team_id", "as_of"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    team_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("team.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    games_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
```

- [ ] **Step 6: Export from `src/analytis/persistence/orm/__init__.py`**

Add `EloHistoryORM` to imports + `__all__`:

```python
from analytis.persistence.orm.elo import EloHistoryORM
```

Add `"EloHistoryORM"` to `__all__` (keep alphabetical).

- [ ] **Step 7: Generate Alembic migration**

```bash
export PATH="/c/Users/PC Gamer/AppData/Local/Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe:$PATH"
export ANALYTIS_DATABASE_URL="postgresql+psycopg://analytis:analytis_dev@localhost:5434/analytis"
export ANALYTIS_API_KEY="local-dev"
uv run alembic revision --autogenerate -m "elo history and team confederation"
```

Rename generated file to `migrations/versions/0002_elo_history_and_confederations.py`. In the file body, set:
- `revision: str = "0002"`
- `down_revision: str | None = "0001"`

- [ ] **Step 8: Apply migration**

```bash
uv run alembic upgrade head
docker exec analytis-postgres psql -U analytis -d analytis -c "\d elo_history"
docker exec analytis-postgres psql -U analytis -d analytis -c "\d team" | head -10
```

Expected: `elo_history` table exists; `team` has `confederation` column.

- [ ] **Step 9: Run tests + quality**

```bash
uv run pytest tests/unit/domain/test_elo.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 3 tests pass, clean.

- [ ] **Step 10: Commit**

```bash
git add src/analytis/domain/elo.py src/analytis/persistence/orm/elo.py src/analytis/persistence/orm/__init__.py src/analytis/persistence/orm/catalog.py migrations/versions/0002_elo_history_and_confederations.py tests/unit/domain/test_elo.py
git commit -m "feat(domain,persistence): add EloRating entity and elo_history table"
```

---

## Task 4: Adapter `InternationalResultsAdapter` (CSV)

**Files:**
- Create: `src/analytis/ingestion/adapters/international_results.py`
- Test: `tests/unit/ingestion/adapters/test_international_results.py`

The dataset CSV columns (from martj42/international_results): `date,home_team,away_team,home_score,away_score,tournament,city,country,neutral`. Team names are full English names ("Brazil", "United States", not codes).

- [ ] **Step 1: Write test — `tests/unit/ingestion/adapters/test_international_results.py`**

```python
"""Unit tests for the International Results CSV adapter."""

from datetime import UTC, datetime

import httpx
import pytest
import respx

from analytis.ingestion.adapters.international_results import (
    InternationalResultsAdapter,
)

URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"

CSV_FIXTURE = (
    "date,home_team,away_team,home_score,away_score,tournament,city,country,neutral\n"
    "2018-06-14,Russia,Saudi Arabia,5,0,FIFA World Cup,Moscow,Russia,False\n"
    "2018-06-15,Egypt,Uruguay,0,1,FIFA World Cup,Yekaterinburg,Russia,True\n"
    "2022-11-20,Qatar,Ecuador,0,2,FIFA World Cup,Al Khor,Qatar,False\n"
)


@pytest.mark.asyncio
async def test_fetch_matches_parses_csv() -> None:
    with respx.mock() as mock:
        mock.get(URL).respond(200, text=CSV_FIXTURE)
        async with httpx.AsyncClient() as client:
            adapter = InternationalResultsAdapter(client=client, url=URL)
            matches = list(await adapter.fetch_matches())

    assert len(matches) == 3
    m0 = matches[0]
    assert m0.home_team_name == "Russia"
    assert m0.away_team_name == "Saudi Arabia"
    assert m0.home_goals == 5
    assert m0.away_goals == 0
    assert m0.kickoff_utc == datetime(2018, 6, 14, 12, 0, tzinfo=UTC)
    assert m0.tournament == "FIFA World Cup"
    assert m0.is_neutral is False
    assert matches[1].is_neutral is True


@pytest.mark.asyncio
async def test_fetch_matches_filters_by_tournament() -> None:
    with respx.mock() as mock:
        mock.get(URL).respond(200, text=CSV_FIXTURE)
        async with httpx.AsyncClient() as client:
            adapter = InternationalResultsAdapter(client=client, url=URL)
            wc = list(
                await adapter.fetch_matches(tournaments={"FIFA World Cup"})
            )

    assert len(wc) == 3


@pytest.mark.asyncio
async def test_fetch_matches_filters_by_date() -> None:
    with respx.mock() as mock:
        mock.get(URL).respond(200, text=CSV_FIXTURE)
        async with httpx.AsyncClient() as client:
            adapter = InternationalResultsAdapter(client=client, url=URL)
            recent = list(
                await adapter.fetch_matches(min_date=datetime(2022, 1, 1, tzinfo=UTC))
            )

    assert len(recent) == 1
    assert recent[0].home_team_name == "Qatar"
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/ingestion/adapters/test_international_results.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/analytis/ingestion/adapters/international_results.py`**

```python
"""Adapter for martj42/international_results CSV dataset.

Source: https://github.com/martj42/international_results
License: CC0 (public domain). Contains every international football match
played since 1872 — ~45,000 rows, updated regularly.
"""

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from io import StringIO

import httpx

from analytis.ingestion.retry import with_retry


@dataclass(frozen=True)
class InternationalMatchDTO:
    source_id: str
    external_id: str  # synthetic: "{date}-{home}-{away}"
    home_team_name: str
    away_team_name: str
    home_goals: int
    away_goals: int
    kickoff_utc: datetime
    tournament: str
    city: str | None
    host_country: str | None
    is_neutral: bool


class InternationalResultsAdapter:
    source_id = "intl_results"
    DEFAULT_URL = (
        "https://raw.githubusercontent.com/"
        "martj42/international_results/master/results.csv"
    )

    def __init__(self, client: httpx.AsyncClient, url: str | None = None) -> None:
        self._client = client
        self._url = url or self.DEFAULT_URL

    @with_retry(max_attempts=3, base_delay=1.0)
    async def _download(self) -> str:
        response = await self._client.get(self._url, timeout=60.0)
        response.raise_for_status()
        return response.text

    async def fetch_matches(
        self,
        tournaments: set[str] | None = None,
        min_date: datetime | None = None,
    ) -> Iterable[InternationalMatchDTO]:
        raw = await self._download()
        reader = csv.DictReader(StringIO(raw))
        result: list[InternationalMatchDTO] = []
        for row in reader:
            tour = row["tournament"].strip()
            if tournaments is not None and tour not in tournaments:
                continue
            d = date.fromisoformat(row["date"].strip())
            kickoff = datetime(d.year, d.month, d.day, 12, 0, tzinfo=UTC)
            if min_date is not None and kickoff < min_date:
                continue
            home = row["home_team"].strip()
            away = row["away_team"].strip()
            result.append(
                InternationalMatchDTO(
                    source_id=self.source_id,
                    external_id=f"{row['date'].strip()}_{home}_{away}".replace(
                        " ", "_"
                    ),
                    home_team_name=home,
                    away_team_name=away,
                    home_goals=int(row["home_score"]),
                    away_goals=int(row["away_score"]),
                    kickoff_utc=kickoff,
                    tournament=tour,
                    city=row["city"].strip() or None,
                    host_country=row["country"].strip() or None,
                    is_neutral=row["neutral"].strip().lower() == "true",
                )
            )
        return result
```

- [ ] **Step 4: Run tests + quality**

```bash
uv run pytest tests/unit/ingestion/adapters/test_international_results.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 3 tests pass, clean.

- [ ] **Step 5: Commit**

```bash
git add src/analytis/ingestion/adapters/international_results.py tests/unit/ingestion/adapters/test_international_results.py
git commit -m "feat(ingestion): add international results CSV adapter"
```

---

## Task 5: Use case `IngestInternationalHistoryUseCase` + CLI

**Files:**
- Create: `src/analytis/application/ingest_international_history.py`
- Modify: `src/analytis/cli/ingest.py`
- Test: `tests/integration/ingestion/test_international_history.py`

- [ ] **Step 1: Write integration test — `tests/integration/ingestion/test_international_history.py`**

```python
"""Integration test for international history ingestion."""

from collections.abc import Iterable
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.ingest_international_history import (
    IngestInternationalHistoryUseCase,
    InternationalHistoryParams,
)
from analytis.ingestion.adapters.international_results import (
    InternationalMatchDTO,
)
from analytis.persistence.orm.matches import MatchORM


class _FakeAdapter:
    source_id = "intl_results"

    def __init__(self, matches: list[InternationalMatchDTO]) -> None:
        self._matches = matches

    async def fetch_matches(
        self,
        tournaments: set[str] | None = None,
        min_date: datetime | None = None,
    ) -> Iterable[InternationalMatchDTO]:
        return list(self._matches)


@pytest.mark.integration
async def test_ingest_history_end_to_end(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    matches = [
        InternationalMatchDTO(
            source_id="intl_results",
            external_id="2018-06-14_Russia_Saudi_Arabia",
            home_team_name="Russia",
            away_team_name="Saudi Arabia",
            home_goals=5,
            away_goals=0,
            kickoff_utc=datetime(2018, 6, 14, 12, 0, tzinfo=UTC),
            tournament="FIFA World Cup",
            city="Moscow",
            host_country="Russia",
            is_neutral=False,
        ),
        InternationalMatchDTO(
            source_id="intl_results",
            external_id="2022-11-20_Qatar_Ecuador",
            home_team_name="Qatar",
            away_team_name="Ecuador",
            home_goals=0,
            away_goals=2,
            kickoff_utc=datetime(2022, 11, 20, 12, 0, tzinfo=UTC),
            tournament="FIFA World Cup",
            city="Al Khor",
            host_country="Qatar",
            is_neutral=False,
        ),
    ]

    use_case = IngestInternationalHistoryUseCase(
        session_factory, adapter=_FakeAdapter(matches)  # type: ignore[arg-type]
    )

    result = await use_case.execute(
        InternationalHistoryParams(tournaments={"FIFA World Cup"})
    )
    assert result.records_touched == 2

    async with session_factory() as s:
        match_count = await s.scalar(select(func.count()).select_from(MatchORM))
        assert match_count == 2

    # Idempotency
    result2 = await use_case.execute(
        InternationalHistoryParams(tournaments={"FIFA World Cup"})
    )
    assert result2.records_touched == 2
    async with session_factory() as s:
        match_count2 = await s.scalar(select(func.count()).select_from(MatchORM))
        assert match_count2 == 2
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/integration/ingestion/test_international_history.py -v -m integration
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/analytis/application/ingest_international_history.py`**

```python
"""Use case: ingest international match history from CSV dataset."""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.confederation import confederation_of_country
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.ingestion.adapters.international_results import (
    InternationalResultsAdapter,
)
from analytis.ingestion.pipeline import IngestionPipeline, IngestionResult
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass
class InternationalHistoryParams:
    tournaments: set[str] = field(default_factory=lambda: {"FIFA World Cup"})
    min_date: datetime | None = None


_COMPETITION_SLUG = {
    "FIFA World Cup": "fifa-world-cup-history",
    "UEFA Euro": "uefa-euro-history",
    "Copa America": "copa-america-history",
    "African Cup of Nations": "afcon-history",
    "AFC Asian Cup": "afc-asian-cup-history",
}


def _slug_for(tournament: str) -> str:
    return _COMPETITION_SLUG.get(
        tournament, tournament.lower().replace(" ", "-") + "-history"
    )


def _country_code_for_team(_name: str) -> str:
    return "UNK"


class IngestInternationalHistoryUseCase:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        adapter: InternationalResultsAdapter,
    ) -> None:
        self._factory = session_factory
        self._adapter = adapter
        self._pipeline = IngestionPipeline(session_factory, adapter.source_id)

    async def execute(
        self, params: InternationalHistoryParams
    ) -> IngestionResult:
        async def job(uow: UnitOfWork) -> IngestionResult:
            matches = list(
                await self._adapter.fetch_matches(
                    tournaments=params.tournaments,
                    min_date=params.min_date,
                )
            )

            comp_repo = CompetitionRepository(uow.session)
            season_repo = SeasonRepository(uow.session)
            team_repo = TeamRepository(uow.session)
            match_repo = MatchRepository(uow.session)

            comps_by_tour: dict[str, Competition] = {}
            for tour in {m.tournament for m in matches}:
                domain_comp = Competition(
                    name=tour,
                    slug=_slug_for(tour),
                    competition_type=CompetitionType.SELECAO,
                    country="INTL",
                    external_ids={self._adapter.source_id: tour},
                )
                await comp_repo.upsert(domain_comp)
                stored = await comp_repo.get_by_slug(domain_comp.slug)
                assert stored is not None
                comps_by_tour[tour] = stored

            seasons_by_key: dict[tuple[str, str], Season] = {}
            for m in matches:
                year_label = str(m.kickoff_utc.year)
                key = (m.tournament, year_label)
                if key in seasons_by_key:
                    continue
                season = Season(
                    competition_id=comps_by_tour[m.tournament].id,
                    label=year_label,
                )
                await season_repo.upsert(season)
                stored = await season_repo.get(
                    comps_by_tour[m.tournament].id, year_label
                )
                assert stored is not None
                seasons_by_key[key] = stored

            team_by_name: dict[str, Team] = {}
            for m in matches:
                for name in (m.home_team_name, m.away_team_name):
                    if name in team_by_name:
                        continue
                    existing = await team_repo.get_by_name(name)
                    if existing is not None:
                        team_by_name[name] = existing
                        continue
                    new_team = Team(
                        name=name,
                        short_name=name[:5].upper(),
                        team_type=TeamType.SELECAO,
                        country=_country_code_for_team(name),
                        external_ids={self._adapter.source_id: name},
                    )
                    await team_repo.upsert(new_team)
                    persisted = await team_repo.get_by_name(name)
                    assert persisted is not None
                    team_by_name[name] = persisted

            touched = 0
            for m in matches:
                home = team_by_name[m.home_team_name]
                away = team_by_name[m.away_team_name]
                season = seasons_by_key[(m.tournament, str(m.kickoff_utc.year))]
                domain_match = Match(
                    season_id=season.id,
                    home_team_id=home.id,
                    away_team_id=away.id,
                    kickoff_utc=m.kickoff_utc,
                    is_home_neutral=m.is_neutral,
                    status=MatchStatus.FINISHED,
                    home_goals=m.home_goals,
                    away_goals=m.away_goals,
                    external_ids={self._adapter.source_id: m.external_id},
                )
                await match_repo.upsert(domain_match)
                touched += 1

            return IngestionResult(records_touched=touched)

        return await self._pipeline.run(
            job_name=f"ingest:intl-history:{','.join(sorted(params.tournaments))}",
            job=job,
        )
```

- [ ] **Step 4: Add CLI command — modify `src/analytis/cli/ingest.py`**

Add at the bottom of the file:

```python
@app.command()
def history(
    tournament: list[str] = typer.Option(  # noqa: B008
        ["FIFA World Cup"], "--tournament", help="Tournament name(s) to filter."
    ),
    since: str = typer.Option(
        "2010-01-01", help="Minimum date (YYYY-MM-DD)."
    ),
) -> None:
    """Ingest international match history from the open CSV dataset."""
    asyncio.run(_history(tournament, since))


async def _history(tournaments: list[str], since: str) -> None:
    from datetime import UTC, datetime as _dt
    from analytis.application.ingest_international_history import (
        IngestInternationalHistoryUseCase,
        InternationalHistoryParams,
    )
    from analytis.ingestion.adapters.international_results import (
        InternationalResultsAdapter,
    )

    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            adapter = InternationalResultsAdapter(client=client)
            use_case = IngestInternationalHistoryUseCase(factory, adapter)
            params = InternationalHistoryParams(
                tournaments=set(tournaments),
                min_date=_dt.fromisoformat(since).replace(tzinfo=UTC),
            )
            result = await use_case.execute(params)
        console.print(
            f"[green]Ingested {result.records_touched} historical matches "
            f"({', '.join(sorted(tournaments))} since {since})[/green]"
        )
    finally:
        await engine.dispose()
```

- [ ] **Step 5: Run tests + quality**

```bash
uv run pytest tests/integration/ingestion/test_international_history.py -v -m integration
uv run mypy src tests
uv run ruff check .
```

Expected: 1 integration test passes.

- [ ] **Step 6: Smoke-test the CLI against the real dataset (small subset)**

```bash
uv run analytis ingest history --tournament "FIFA World Cup" --since 2018-01-01
docker exec analytis-postgres psql -U analytis -d analytis -c \
  "SELECT s.label, COUNT(*) FROM match m JOIN season s ON s.id=m.season_id JOIN competition c ON s.competition_id=c.id WHERE c.slug='fifa-world-cup-history' GROUP BY s.label ORDER BY s.label;"
```

Expected: rows like `2018 | 64`, `2022 | 64` (Copa do Mundo tem 64 jogos por edição até 2026).

- [ ] **Step 7: Commit**

```bash
git add src/analytis/application/ingest_international_history.py src/analytis/cli/ingest.py tests/integration/ingestion/test_international_history.py
git commit -m "feat(application,cli): ingest international history (CSV dataset)"
```

---

## Task 6: ELO math core + tests

**Files:**
- Create: `src/analytis/features/__init__.py` (empty)
- Create: `src/analytis/features/elo.py`
- Test: `tests/unit/features/__init__.py` (empty)
- Test: `tests/unit/features/test_elo_math.py`

- [ ] **Step 1: Create empty `__init__.py` files**

```python
# src/analytis/features/__init__.py
```

```python
# tests/unit/features/__init__.py
```

- [ ] **Step 2: Write test — `tests/unit/features/test_elo_math.py`**

```python
"""Tests for World Football Elo math primitives."""

import pytest

from analytis.features.elo import (
    DEFAULT_RATING,
    expected_score,
    k_factor,
    update_ratings,
)


def test_expected_score_equal_strength() -> None:
    assert expected_score(1500.0, 1500.0) == pytest.approx(0.5, abs=1e-9)


def test_expected_score_stronger_home() -> None:
    es = expected_score(1700.0, 1500.0)
    assert 0.5 < es < 1.0
    assert es == pytest.approx(0.7597, abs=1e-3)


def test_expected_score_with_home_advantage() -> None:
    es_neutral = expected_score(1500.0, 1500.0, home_advantage=0.0)
    es_home = expected_score(1500.0, 1500.0, home_advantage=100.0)
    assert es_home > es_neutral


def test_k_factor_world_cup_higher_than_friendly() -> None:
    assert k_factor("FIFA World Cup") > k_factor("Friendly")


def test_k_factor_unknown_falls_back() -> None:
    assert k_factor("Some Obscure Tournament") == k_factor("Friendly")


def test_update_ratings_winner_gains_loser_loses() -> None:
    new_home, new_away = update_ratings(
        home_rating=1500.0,
        away_rating=1500.0,
        home_goals=2,
        away_goals=0,
        tournament="FIFA World Cup",
        is_neutral=True,
    )
    assert new_home > 1500.0
    assert new_away < 1500.0
    assert new_home + new_away == pytest.approx(3000.0, abs=1e-9)


def test_update_ratings_draw_zero_sum_around_expected() -> None:
    new_home, new_away = update_ratings(
        home_rating=1500.0,
        away_rating=1500.0,
        home_goals=1,
        away_goals=1,
        tournament="FIFA World Cup",
        is_neutral=True,
    )
    assert new_home == pytest.approx(1500.0, abs=1e-6)
    assert new_away == pytest.approx(1500.0, abs=1e-6)


def test_blowout_more_points_than_narrow_win() -> None:
    h_narrow, _ = update_ratings(
        1500.0, 1500.0, 1, 0,
        tournament="FIFA World Cup", is_neutral=True,
    )
    h_blowout, _ = update_ratings(
        1500.0, 1500.0, 5, 0,
        tournament="FIFA World Cup", is_neutral=True,
    )
    assert h_blowout > h_narrow


def test_default_rating_is_1500() -> None:
    assert DEFAULT_RATING == 1500.0
```

- [ ] **Step 3: Verify failure**

```bash
uv run pytest tests/unit/features/test_elo_math.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement `src/analytis/features/elo.py`**

```python
"""World Football Elo math primitives.

Adapted from the formula at https://www.eloratings.net/about — key choices:
- Logistic with scale 400.
- Home advantage 100 (subtractable to zero for neutral venues).
- Goal-difference multiplier as on eloratings.net.
- K-factor scaled by competition importance.
"""

import math

DEFAULT_RATING: float = 1500.0
HOME_ADVANTAGE: float = 100.0

_TOURNAMENT_K: dict[str, float] = {
    "FIFA World Cup": 60.0,
    "Copa America": 50.0,
    "UEFA Euro": 50.0,
    "African Cup of Nations": 50.0,
    "AFC Asian Cup": 50.0,
    "FIFA World Cup qualification": 40.0,
    "UEFA Nations League": 40.0,
    "Confederations Cup": 40.0,
    "Friendly": 20.0,
}
_DEFAULT_K: float = 20.0


def k_factor(tournament: str) -> float:
    return _TOURNAMENT_K.get(tournament, _DEFAULT_K)


def expected_score(
    rating_a: float, rating_b: float, home_advantage: float = HOME_ADVANTAGE
) -> float:
    """Logistic expected score for player A against B (scale 400)."""
    diff = rating_a + home_advantage - rating_b
    return 1.0 / (1.0 + math.pow(10.0, -diff / 400.0))


def _goal_diff_multiplier(goal_diff: int) -> float:
    g = abs(goal_diff)
    if g <= 1:
        return 1.0
    if g == 2:
        return 1.5
    return (11.0 + g) / 8.0


def _outcome(home_goals: int, away_goals: int) -> float:
    if home_goals > away_goals:
        return 1.0
    if home_goals < away_goals:
        return 0.0
    return 0.5


def update_ratings(
    home_rating: float,
    away_rating: float,
    home_goals: int,
    away_goals: int,
    tournament: str,
    is_neutral: bool,
) -> tuple[float, float]:
    """Return new (home_rating, away_rating) after a single match."""
    ha = 0.0 if is_neutral else HOME_ADVANTAGE
    es = expected_score(home_rating, away_rating, home_advantage=ha)
    actual = _outcome(home_goals, away_goals)
    k = k_factor(tournament) * _goal_diff_multiplier(home_goals - away_goals)
    delta = k * (actual - es)
    return home_rating + delta, away_rating - delta
```

- [ ] **Step 5: Run tests + quality**

```bash
uv run pytest tests/unit/features/test_elo_math.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 9 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/analytis/features/__init__.py src/analytis/features/elo.py tests/unit/features/__init__.py tests/unit/features/test_elo_math.py
git commit -m "feat(features): add World Football Elo math primitives"
```

---

## Task 7: EloHistoryRepository + ELO computation pipeline

**Files:**
- Create: `src/analytis/persistence/repositories/elo.py`
- Modify: `src/analytis/persistence/repositories/__init__.py`
- Create: `src/analytis/application/compute_elo_history.py`
- Test: `tests/integration/application/__init__.py` (empty)
- Test: `tests/integration/application/test_compute_elo_history.py`

- [ ] **Step 1: Create `src/analytis/persistence/repositories/elo.py`**

```python
"""Repository for ELO history."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.domain.elo import EloRating
from analytis.persistence.orm.elo import EloHistoryORM


def _to_domain(orm: EloHistoryORM) -> EloRating:
    return EloRating(
        id=orm.id,
        team_id=orm.team_id,
        rating=orm.rating,
        as_of=orm.as_of,
        games_played=orm.games_played,
    )


class EloHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest_for_team(
        self, team_id: UUID, as_of: datetime
    ) -> EloRating | None:
        result = await self._session.scalars(
            select(EloHistoryORM)
            .where(
                EloHistoryORM.team_id == team_id,
                EloHistoryORM.as_of <= as_of,
            )
            .order_by(EloHistoryORM.as_of.desc())
            .limit(1)
        )
        orm = result.one_or_none()
        return _to_domain(orm) if orm else None

    async def insert(self, rating: EloRating) -> None:
        self._session.add(
            EloHistoryORM(
                id=rating.id,
                team_id=rating.team_id,
                rating=rating.rating,
                as_of=rating.as_of,
                games_played=rating.games_played,
            )
        )

    async def clear_all(self) -> None:
        await self._session.execute(delete(EloHistoryORM))
```

- [ ] **Step 2: Update `src/analytis/persistence/repositories/__init__.py`**

Add to imports + `__all__` (keep alphabetical):

```python
from analytis.persistence.repositories.elo import EloHistoryRepository
```

- [ ] **Step 3: Create `src/analytis/application/compute_elo_history.py`**

```python
"""Use case: compute ELO history from finished matches in chronological order."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from analytis.domain.elo import EloRating
from analytis.features.elo import DEFAULT_RATING, update_ratings
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.repositories import EloHistoryRepository
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass
class ComputeEloResult:
    teams_seen: int
    ratings_written: int


class ComputeEloHistoryUseCase:
    def __init__(
        self, session_factory: async_sessionmaker
    ) -> None:
        self._factory = session_factory

    async def execute(self, *, reset: bool = True) -> ComputeEloResult:
        async with UnitOfWork(self._factory) as uow:
            elo_repo = EloHistoryRepository(uow.session)
            if reset:
                await elo_repo.clear_all()

            stmt = (
                select(MatchORM)
                .where(
                    MatchORM.status == "finished",
                    MatchORM.home_goals.is_not(None),
                    MatchORM.away_goals.is_not(None),
                )
                .order_by(MatchORM.kickoff_utc.asc())
            )
            result = await uow.session.scalars(stmt)
            matches = list(result.all())

            current: dict = {}
            games: dict = {}

            for m in matches:
                h_rating = current.get(m.home_team_id, DEFAULT_RATING)
                a_rating = current.get(m.away_team_id, DEFAULT_RATING)

                # tournament inference from competition name happens later;
                # for ELO compute we default to "Friendly" when no competition
                # info is available. Refinement comes from richer matches.
                tournament = await self._tournament_for(uow, m.id)

                assert m.home_goals is not None and m.away_goals is not None
                new_h, new_a = update_ratings(
                    home_rating=h_rating,
                    away_rating=a_rating,
                    home_goals=m.home_goals,
                    away_goals=m.away_goals,
                    tournament=tournament,
                    is_neutral=m.is_home_neutral,
                )
                current[m.home_team_id] = new_h
                current[m.away_team_id] = new_a
                games[m.home_team_id] = games.get(m.home_team_id, 0) + 1
                games[m.away_team_id] = games.get(m.away_team_id, 0) + 1

                await elo_repo.insert(
                    EloRating(
                        team_id=m.home_team_id,
                        rating=new_h,
                        as_of=m.kickoff_utc,
                        games_played=games[m.home_team_id],
                    )
                )
                await elo_repo.insert(
                    EloRating(
                        team_id=m.away_team_id,
                        rating=new_a,
                        as_of=m.kickoff_utc,
                        games_played=games[m.away_team_id],
                    )
                )

            return ComputeEloResult(
                teams_seen=len(current), ratings_written=2 * len(matches)
            )

    async def _tournament_for(
        self, uow: UnitOfWork, _match_id
    ) -> str:
        # Simplified: use competition name as tournament. A richer
        # implementation would JOIN season -> competition; we keep it simple
        # for now and rely on Friendly default for non-WC matches.
        return "FIFA World Cup"
```

- [ ] **Step 4: Write integration test — `tests/integration/application/test_compute_elo_history.py`**

```python
"""Integration test for ELO history computation."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.compute_elo_history import ComputeEloHistoryUseCase
from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.persistence.orm.elo import EloHistoryORM
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


async def _seed_minimal(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with UnitOfWork(session_factory) as uow:
        crepo = CompetitionRepository(uow.session)
        srepo = SeasonRepository(uow.session)
        trepo = TeamRepository(uow.session)
        mrepo = MatchRepository(uow.session)
        comp = Competition(
            name="FIFA World Cup", slug="fifa-world-cup-history",
            competition_type=CompetitionType.SELECAO, country="INTL",
        )
        await crepo.upsert(comp)
        stored_comp = await crepo.get_by_slug("fifa-world-cup-history")
        assert stored_comp is not None
        season = Season(competition_id=stored_comp.id, label="2018")
        await srepo.upsert(season)
        stored_season = await srepo.get(stored_comp.id, "2018")
        assert stored_season is not None
        for n in ["Brazil", "Mexico", "Belgium"]:
            await trepo.upsert(Team(
                name=n, short_name=n[:5].upper(),
                team_type=TeamType.SELECAO, country="INT",
            ))
        bra = await trepo.get_by_name("Brazil")
        mex = await trepo.get_by_name("Mexico")
        bel = await trepo.get_by_name("Belgium")
        assert bra and mex and bel
        for ext, (h, a, hg, ag, when) in enumerate([
            (bra.id, mex.id, 2, 0, datetime(2018, 7, 2, 12, tzinfo=UTC)),
            (bel.id, bra.id, 2, 1, datetime(2018, 7, 6, 12, tzinfo=UTC)),
        ]):
            await mrepo.upsert(Match(
                season_id=stored_season.id,
                home_team_id=h, away_team_id=a,
                kickoff_utc=when, is_home_neutral=True,
                status=MatchStatus.FINISHED,
                home_goals=hg, away_goals=ag,
                external_ids={"test": f"m{ext}"},
            ))


@pytest.mark.integration
async def test_compute_elo_history_basic(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed_minimal(session_factory)
    use_case = ComputeEloHistoryUseCase(session_factory)
    result = await use_case.execute()
    assert result.teams_seen == 3
    assert result.ratings_written == 4  # 2 matches × 2 teams

    async with session_factory() as s:
        count = await s.scalar(select(func.count()).select_from(EloHistoryORM))
        assert count == 4
```

- [ ] **Step 5: Run tests + quality**

```bash
uv run pytest tests/integration/application/test_compute_elo_history.py -v -m integration
uv run mypy src tests
uv run ruff check .
```

Expected: 1 test passes.

- [ ] **Step 6: Commit**

```bash
git add src/analytis/persistence/repositories/elo.py src/analytis/persistence/repositories/__init__.py src/analytis/application/compute_elo_history.py tests/integration/application/__init__.py tests/integration/application/test_compute_elo_history.py
git commit -m "feat(application): compute ELO history from finished matches"
```

---

## Task 8: Feature registry + ELO-derived features

**Files:**
- Create: `src/analytis/features/registry.py`
- Create: `src/analytis/features/strength.py`
- Test: `tests/unit/features/test_registry.py`

- [ ] **Step 1: Write test — `tests/unit/features/test_registry.py`**

```python
"""Tests for the feature registry."""

import pytest

from analytis.features.registry import FeatureRegistry


@pytest.mark.asyncio
async def test_registry_register_and_compute() -> None:
    reg = FeatureRegistry()

    @reg.register("constant_one")
    async def _const(_ctx: object) -> float:
        return 1.0

    @reg.register("constant_two")
    async def _two(_ctx: object) -> float:
        return 2.0

    out = await reg.compute_all(context=None)
    assert out == {"constant_one": 1.0, "constant_two": 2.0}


def test_registry_rejects_duplicate_name() -> None:
    reg = FeatureRegistry()

    @reg.register("dup")
    async def _a(_ctx: object) -> float:
        return 0.0

    with pytest.raises(ValueError, match="already registered"):

        @reg.register("dup")
        async def _b(_ctx: object) -> float:
            return 1.0
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/features/test_registry.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/analytis/features/registry.py`**

```python
"""Feature registry — async function map for batch computation."""

from collections.abc import Awaitable, Callable
from typing import Any

FeatureFn = Callable[[Any], Awaitable[float | None]]


class FeatureRegistry:
    def __init__(self) -> None:
        self._fns: dict[str, FeatureFn] = {}

    def register(self, name: str) -> Callable[[FeatureFn], FeatureFn]:
        def _decorator(fn: FeatureFn) -> FeatureFn:
            if name in self._fns:
                raise ValueError(f"feature {name!r} already registered")
            self._fns[name] = fn
            return fn

        return _decorator

    def names(self) -> list[str]:
        return list(self._fns.keys())

    async def compute_all(self, context: Any) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for name, fn in self._fns.items():
            result[name] = await fn(context)
        return result
```

- [ ] **Step 4: Implement `src/analytis/features/strength.py`** (placeholder — full strength features land in Task 9)

```python
"""Team strength features (filled in Task 9; placeholder for imports)."""

from analytis.features.registry import FeatureRegistry

strength_registry = FeatureRegistry()
```

- [ ] **Step 5: Run tests + quality**

```bash
uv run pytest tests/unit/features/test_registry.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 2 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/analytis/features/registry.py src/analytis/features/strength.py tests/unit/features/test_registry.py
git commit -m "feat(features): registry for async feature functions"
```

---

## Task 9 onward (overview)

The remaining tasks are decomposed at the same granularity as Tasks 1-8, each with: file list, failing test, implementation, runs, commit. They cover:

### Task 9: Strength features with Bayesian shrinkage by confederation
Builds attack/defense feature pair shrunk toward the team's confederation mean. Test: empty-history team returns confederation prior; team with many games returns observed mean.

### Task 10: Form features (rolling windows with exponential decay)
`form_last_5_goals_scored`, `form_last_5_goals_conceded`, `form_xg_proxy` over a configurable window with half-life parameter. Test: ramp series produces monotonically increasing form when weighted recent.

### Task 11: Context features (rest, neutral, stage, H2H)
`rest_days_home`, `rest_days_away`, `is_neutral`, `is_eliminatorio`, `h2h_home_wins_last_n`, `h2h_goal_diff_avg`. Tests cover edge cases (first match for team → rest_days=None; no prior H2H → 0/NULL).

### Task 12: Feature snapshot builder + repository
`FeatureSnapshotRepository.insert` (uses existing `feature_snapshot` ORM). Builder assembles a vector via the registry, persists as JSONB. Integration test: build for a known match, verify shape and reproducibility.

### Task 13: Dixon-Coles math core
Bivariate Poisson with low-score correction. Functions: `tau(i, j, lambda_home, lambda_away, rho)`, `log_likelihood(params, matches, decay)`, `score_matrix(lambda_home, lambda_away, rho, max_goals=10)`. Property tests verify matrix sums to 1 ± 1e-9.

### Task 14: Dixon-Coles fitter via scipy
L-BFGS over `(attack_i, defense_i for each team, home_advantage, rho)`. Decay weights via `exp(-xi * days_ago)`. Convergence test on synthetic data: known params recovered within tolerance.

### Task 15: Market derivations (1X2, Over/Under 2.5, BTTS)
Given a score matrix, derive: `p_home_win`, `p_draw`, `p_away_win` (sums of regions); `p_over_2_5`, `p_under_2_5`; `p_btts_yes`, `p_btts_no`. Property test: each market's probabilities sum to 1.

### Task 16: Bayesian confederation prior + shrinkage applied to DC parameters
Hyper-prior over `attack`/`defense` by confederation; integrated into the L-BFGS objective via a Gaussian penalty term. Test: a team with few games is pulled toward its confederation mean.

### Task 17: Model fitting persistence (save/load) + ModelVersion repository
Pickle the fitted parameters under `models/{version_id}.pkl`, record `model_version` with git SHA, hyperparams, metrics. Integration test: train → persist → reload → identical predictions.

### Task 18: Evaluation metrics (Brier, log-loss, reliability)
`brier_score(probs, outcomes)`, `log_loss(probs, outcomes)`, `expected_calibration_error(probs, outcomes, n_bins=10)`, `reliability_diagram_data(...)`. Property tests on calibrated synthetic distributions.

### Task 19: Walk-forward CV
Slices: train on `[t0, t]`, score on `(t, t+1 month]`, advance. Returns per-slice metrics. Integration test: end-to-end over a small synthetic dataset.

### Task 20: `TrainDixonColesUseCase` + CLI `analytis train dixon-coles`
Orchestrates: load matches → build features → fit DC → persist ModelVersion. Smoke test: training over the 2018+2022 World Cup data converges and writes a `model_version` row.

### Task 21: `ScoreMatchUseCase` + CLI `analytis score`
For each upcoming Copa 2026 match: snapshot features → run fitted DC → derive markets → insert `prediction` rows with bootstrap CIs. Idempotency: same `(match, model, snapshot)` doesn't duplicate.

### Task 22: `BacktestUseCase` + CLI `analytis backtest`
Runs walk-forward CV over Copa 2018 + 2022 + finished portion of 2026. Writes a JSON report to `models/{version}/backtest.json` and a `model_version.metrics` summary.

### Task 23: API routes for predictions + model metrics
`GET /v1/matches/{id}/predictions` — returns market probabilities + CIs + diagnostics block.
`GET /v1/models/{version_id}/metrics` — returns evaluation summary.

### Task 24: README update + acceptance criteria check
Add usage examples for the new commands. Run all acceptance criteria below.

---

## Acceptance Criteria (end-of-plan checklist)

- [ ] `uv run analytis ingest history --tournament "FIFA World Cup" --since 2010-01-01` loads at least 192 matches (2010, 2014, 2018, 2022 × 64).
- [ ] After ingest, `SELECT COUNT(DISTINCT name) FROM team` ≥ 50 (Copa 2026 ingested previously + historical opponents).
- [ ] `uv run analytis features build --match <any-2026-match-id>` produces a `feature_snapshot` row with non-null `elo_diff`, `home_advantage`, `rest_days_home`, etc.
- [ ] `uv run analytis train dixon-coles --since 2010-01-01` writes one `model_version` row with Brier on holdout ≤ 0.22 for 1X2 (sanity, not a hard target).
- [ ] `uv run analytis score --all-upcoming` populates `prediction` rows for every scheduled Copa 2026 match, with `ci_low <= prob <= ci_high` enforced by check constraint.
- [ ] `uv run analytis backtest --since 2014-01-01` produces a JSON report under `models/<version>/backtest.json` with per-mercado Brier/log-loss.
- [ ] `GET /v1/matches/{id}/predictions` returns the latest predictions in the documented shape, including a `diagnostics` block.
- [ ] All unit and integration tests pass with coverage ≥ 75% in `features/`, `modeling/`, `application/`.
- [ ] `uv run mypy src tests` and `uv run ruff check .` clean.

If any item fails, add a follow-up task before declaring the plan done.
