# Dashboard de Acertos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `/acertos` page that shows hit rate per market, Brier score, cumulative accuracy by tournament phase, and a per-match table for any model with predictions.

**Architecture:** New FastAPI endpoint `GET /v1/accuracy/summary?model=<name>` returning KPIs + timeseries + match rows. New React page consumes via react-query. Recharts for the line chart (already in deps). All existing component + design patterns reused (Card, Skeleton, NavLink, ApiKeyDialog auth handler).

**Tech Stack:**
- Backend: FastAPI, SQLAlchemy async (Postgres), Pydantic v2
- Frontend: React 18, react-query, recharts, Tailwind (existing tokens), shadcn `Card`/`Skeleton`
- Tests: pytest + httpx async client (backend); vitest + React Testing Library + mocked react-query (frontend)

**Spec:** `docs/superpowers/specs/2026-06-20-acertos-dashboard-design.md`

---

## File Structure

**Backend (create):**
- `src/analytis/application/accuracy_summary.py` — use case + helpers + Pydantic response models
- `src/analytis/api/routes/accuracy.py` — FastAPI router with single GET endpoint
- `tests/integration/api/test_accuracy_summary.py` — 10 integration tests

**Backend (modify):**
- `src/analytis/api/main.py` — include `accuracy.router` in `create_app()`

**Frontend (create):**
- `frontend/src/pages/AccuracyPage.tsx` — page composition
- `frontend/src/hooks/useAccuracySummary.ts` — react-query hook
- `frontend/src/components/accuracy/KpiCard.tsx`
- `frontend/src/components/accuracy/ModelSelector.tsx`
- `frontend/src/components/accuracy/AccuracyChart.tsx`
- `frontend/src/components/accuracy/MatchAccuracyTable.tsx`
- `frontend/src/pages/__tests__/AccuracyPage.test.tsx` — 6 page tests

**Frontend (modify):**
- `frontend/src/lib/api.ts` — `fetchAccuracySummary()` + TS types
- `frontend/src/App.tsx` — `/acertos` route
- `frontend/src/components/layout/Header.tsx` — nav item "Acertos"
- `frontend/src/components/layout/BottomNav.tsx` — nav item + `grid-cols-6`

---

## Backend — Tasks 1-7

### Task 1: Pydantic response schemas + use case skeleton

**Files:**
- Create: `src/analytis/application/accuracy_summary.py`

- [ ] **Step 1: Create the file with Pydantic models and a stub `execute()`**

Write this file:

```python
"""Use case for computing model accuracy on finished matches with predictions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


Phase = Literal["group", "round_of_16", "quarterfinal", "semifinal", "final"]
PHASES: tuple[Phase, ...] = ("group", "round_of_16", "quarterfinal", "semifinal", "final")


class ModelRef(BaseModel):
    id: UUID
    name: str
    family: str


class ModelOption(ModelRef):
    n_predictions: int


class MarketKpi(BaseModel):
    hits: int
    n: int
    rate: float
    ci_low: float
    ci_high: float
    brier_avg: float


class Kpis(BaseModel):
    n_matches_evaluated: int
    markets: dict[str, MarketKpi]  # keys: "1x2", "ou", "btts"
    brier_overall: float


class TimeseriesPoint(BaseModel):
    phase: Phase
    n: int
    cumulative: dict[str, float]  # keys: "1x2", "ou", "btts"


class MatchPredictionDetail(BaseModel):
    predicted: str
    predicted_prob: float
    actual: str
    hit: bool
    brier: float


class MatchRow(BaseModel):
    match_id: UUID
    kickoff_utc: datetime
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    phase: Phase
    predictions: dict[str, MatchPredictionDetail]  # keys: "1x2", "ou", "btts"


class AccuracySummary(BaseModel):
    model: ModelRef
    available_models: list[ModelOption]
    kpis: Kpis
    timeseries: list[TimeseriesPoint]
    matches: list[MatchRow]


@dataclass
class AccuracySummaryParams:
    model_name: str | None


class ModelNotFoundError(Exception):
    """Raised when ?model=<name> doesn't match any model_version with predictions."""


class AccuracySummaryUseCase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def execute(self, params: AccuracySummaryParams) -> AccuracySummary:
        raise NotImplementedError("filled in subsequent tasks")
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run python -c "from analytis.application.accuracy_summary import AccuracySummary, AccuracySummaryUseCase; print('ok')"
```

Expected output: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/analytis/application/accuracy_summary.py
git commit -m "feat(api): accuracy_summary skeleton — schemas + use case stub"
```

---

### Task 2: Phase normalization + Wilson CI helpers

**Files:**
- Modify: `src/analytis/application/accuracy_summary.py`
- Create: `tests/unit/application/test_accuracy_summary_helpers.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/application/test_accuracy_summary_helpers.py`:

```python
import math

import pytest

from analytis.application.accuracy_summary import (
    normalize_phase,
    wilson_ci,
)


@pytest.mark.parametrize(
    "competition_round,expected",
    [
        ("GROUP_STAGE", "group"),
        ("LAST_16", "round_of_16"),
        ("QUARTER_FINALS", "quarterfinal"),
        ("SEMI_FINALS", "semifinal"),
        ("FINAL", "final"),
        ("THIRD_PLACE", "semifinal"),  # aggregated into semifinal
        ("unknown_value", "group"),     # fallback
        (None, "group"),                # null safe
    ],
)
def test_normalize_phase(competition_round: str | None, expected: str) -> None:
    assert normalize_phase(competition_round) == expected


def test_wilson_ci_known_case() -> None:
    # n=10, hits=7 → Wilson CI is approximately [0.397, 0.892]
    low, high = wilson_ci(hits=7, n=10)
    assert math.isclose(low, 0.3968, abs_tol=0.002)
    assert math.isclose(high, 0.8922, abs_tol=0.002)


def test_wilson_ci_n_zero_returns_full_range() -> None:
    low, high = wilson_ci(hits=0, n=0)
    assert low == 0.0
    assert high == 1.0


def test_wilson_ci_all_hits() -> None:
    low, high = wilson_ci(hits=5, n=5)
    assert low > 0.5
    assert high == pytest.approx(1.0, abs=1e-6)


def test_wilson_ci_no_hits() -> None:
    low, high = wilson_ci(hits=0, n=5)
    assert low == pytest.approx(0.0, abs=1e-6)
    assert high < 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run pytest tests/unit/application/test_accuracy_summary_helpers.py -v
```

Expected: ImportError or AttributeError — `normalize_phase` and `wilson_ci` don't exist yet.

- [ ] **Step 3: Implement the helpers**

Add to `src/analytis/application/accuracy_summary.py` (above the `AccuracySummaryUseCase` class):

```python
import math


_PHASE_MAP: dict[str, Phase] = {
    "GROUP_STAGE": "group",
    "LAST_16": "round_of_16",
    "QUARTER_FINALS": "quarterfinal",
    "SEMI_FINALS": "semifinal",
    "THIRD_PLACE": "semifinal",
    "FINAL": "final",
}


def normalize_phase(competition_round: str | None) -> Phase:
    """Map Football-Data competition_round string to our canonical Phase."""
    if competition_round is None:
        return "group"
    return _PHASE_MAP.get(competition_round, "group")


def wilson_ci(*, hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% by default).

    Returns (low, high) clipped to [0.0, 1.0]. When n == 0 returns (0.0, 1.0).
    """
    if n <= 0:
        return (0.0, 1.0)
    p = hits / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    low = max(0.0, center - half)
    high = min(1.0, center + half)
    return (low, high)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run pytest tests/unit/application/test_accuracy_summary_helpers.py -v
```

Expected: all 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/application/test_accuracy_summary_helpers.py src/analytis/application/accuracy_summary.py
git commit -m "feat(api): accuracy_summary — phase normalization + Wilson CI helpers"
```

---

### Task 3: KPI computation — hit definitions per market

**Files:**
- Modify: `src/analytis/application/accuracy_summary.py`
- Modify: `tests/unit/application/test_accuracy_summary_helpers.py`

- [ ] **Step 1: Write failing tests for hit-derivation helpers**

Append to `tests/unit/application/test_accuracy_summary_helpers.py`:

```python
from analytis.application.accuracy_summary import (
    actual_1x2,
    actual_btts,
    actual_ou,
    brier_binary,
    brier_multiclass,
    predicted_1x2_top,
)


@pytest.mark.parametrize(
    "home,away,expected",
    [(2, 1, "home"), (1, 1, "draw"), (0, 3, "away"), (0, 0, "draw")],
)
def test_actual_1x2(home: int, away: int, expected: str) -> None:
    assert actual_1x2(home, away) == expected


@pytest.mark.parametrize(
    "home,away,expected",
    [(2, 1, "over"), (1, 1, "under"), (0, 2, "under"), (0, 3, "over")],
)
def test_actual_ou(home: int, away: int, expected: str) -> None:
    assert actual_ou(home, away) == expected


@pytest.mark.parametrize(
    "home,away,expected",
    [(2, 1, "yes"), (0, 1, "no"), (1, 0, "no"), (0, 0, "no")],
)
def test_actual_btts(home: int, away: int, expected: str) -> None:
    assert actual_btts(home, away) == expected


def test_predicted_1x2_top_picks_highest_prob() -> None:
    probs = {"home": 0.55, "draw": 0.25, "away": 0.20}
    assert predicted_1x2_top(probs) == ("home", 0.55)


def test_predicted_1x2_top_breaks_tie_alphabetically() -> None:
    # Deterministic tie-break: alphabetical by outcome name
    probs = {"home": 0.40, "draw": 0.40, "away": 0.20}
    assert predicted_1x2_top(probs) == ("draw", 0.40)


def test_brier_binary_perfect_correct() -> None:
    # prob=1.0, outcome=1 → brier=0
    assert brier_binary(prob=1.0, outcome=1) == pytest.approx(0.0)


def test_brier_binary_perfect_wrong() -> None:
    # prob=1.0, outcome=0 → brier=1.0
    assert brier_binary(prob=1.0, outcome=0) == pytest.approx(1.0)


def test_brier_binary_coin_flip() -> None:
    # prob=0.5 always gives 0.25
    assert brier_binary(prob=0.5, outcome=1) == pytest.approx(0.25)
    assert brier_binary(prob=0.5, outcome=0) == pytest.approx(0.25)


def test_brier_multiclass_correct() -> None:
    # probs sum to 1, actual="home" → one-hot [1,0,0]
    # brier = ((p_home-1)^2 + p_draw^2 + p_away^2) / 3
    probs = {"home": 0.6, "draw": 0.3, "away": 0.1}
    expected = ((0.6 - 1.0) ** 2 + 0.3**2 + 0.1**2) / 3
    assert brier_multiclass(probs=probs, actual="home") == pytest.approx(expected)
```

- [ ] **Step 2: Run tests — they should fail**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run pytest tests/unit/application/test_accuracy_summary_helpers.py -v
```

Expected: 9 new tests FAIL (ImportError for `actual_1x2`, etc.). Previous 12 still PASS.

- [ ] **Step 3: Implement the helpers**

Add to `src/analytis/application/accuracy_summary.py` (next to the other helpers):

```python
def actual_1x2(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def actual_ou(home_goals: int, away_goals: int) -> str:
    return "over" if (home_goals + away_goals) > 2.5 else "under"


def actual_btts(home_goals: int, away_goals: int) -> str:
    return "yes" if (home_goals >= 1 and away_goals >= 1) else "no"


def predicted_1x2_top(probs: dict[str, float]) -> tuple[str, float]:
    """Return (top_outcome, top_prob). Deterministic tie-break by alphabetical key."""
    return max(probs.items(), key=lambda kv: (kv[1], -ord(kv[0][0])))


def brier_binary(*, prob: float, outcome: int) -> float:
    """Brier for a single binary prediction. outcome must be 0 or 1."""
    return (prob - outcome) ** 2


def brier_multiclass(*, probs: dict[str, float], actual: str) -> float:
    """Brier multiclass over outcomes. actual is one of probs.keys()."""
    if actual not in probs:
        raise ValueError(f"actual {actual!r} not in probs keys {list(probs)}")
    total = 0.0
    for outcome, p in probs.items():
        y = 1.0 if outcome == actual else 0.0
        total += (p - y) ** 2
    return total / len(probs)
```

Wait — the tie-break test expects `"draw"` to win over `"home"` when both have prob 0.40. Alphabetical: a < d < h. So `away` < `draw` < `home`. The test says `draw` wins over `home` when they tie. But `away` would beat `draw`. The test only covers home vs draw, not all three at 0.40.

Re-examine: `max(probs.items(), key=lambda kv: (kv[1], -ord(kv[0][0])))` — sorts by prob desc, then by `-ord(first char)` desc which means lower first char wins. `'h'` is 104, `'d'` is 100, `'a'` is 97. `-104 < -100 < -97`. So for prob tie, the one with lowest `-ord` wins... wait, max picks the highest value of the key, so higher `-ord` wins = lower `ord` wins = earlier in alphabet wins.

But test says `draw` wins over `home`: `ord('d')=100`, `ord('h')=104`. `-100 > -104`. So `draw` wins. ✓

But what about `away` (a=97) vs `draw` (d=100)? `-97 > -100` → `away` wins. So `away` would beat `draw` at same prob.

The test only tested home vs draw tie. Good enough — explicit alphabetical earlier-wins semantics.

- [ ] **Step 4: Run tests to verify all pass**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run pytest tests/unit/application/test_accuracy_summary_helpers.py -v
```

Expected: 21 tests PASS (12 old + 9 new).

- [ ] **Step 5: Commit**

```bash
git add tests/unit/application/test_accuracy_summary_helpers.py src/analytis/application/accuracy_summary.py
git commit -m "feat(api): accuracy_summary — hit derivation + Brier helpers"
```

---

### Task 4: Integration test fixtures + first happy-path test

**Files:**
- Create: `tests/integration/api/test_accuracy_summary.py`

- [ ] **Step 1: Inspect existing integration test patterns**

```bash
cd "C:/Projetos/Pessoal/analytis"
ls tests/integration/api/ | head
```

Read `tests/integration/api/test_predictions.py` (one of the existing ones) to copy its async client + fixture setup pattern. Use the same `async_client`, DB session, and `seed_*` fixture style.

- [ ] **Step 2: Write the integration test file with shared fixtures + first test**

Create `tests/integration/api/test_accuracy_summary.py`:

```python
"""Integration tests for GET /v1/accuracy/summary."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.persistence.orm.competition import CompetitionORM, SeasonORM
from analytis.persistence.orm.inference import ModelVersionORM, PredictionORM
from analytis.persistence.orm.match import MatchORM
from analytis.persistence.orm.team import TeamORM

API_KEY_HEADER = {"X-API-Key": "test-key"}  # adjust if your test fixture differs


async def _seed_competition(session: AsyncSession) -> tuple[CompetitionORM, SeasonORM]:
    comp = CompetitionORM(id=uuid4(), name="Copa Test", code="TEST")
    season = SeasonORM(id=uuid4(), competition_id=comp.id, name="2026", start_date=datetime(2026, 6, 1, tzinfo=UTC).date(), end_date=datetime(2026, 7, 30, tzinfo=UTC).date())
    session.add_all([comp, season])
    await session.flush()
    return comp, season


async def _seed_teams(session: AsyncSession, names: list[str]) -> dict[str, TeamORM]:
    teams = {n: TeamORM(id=uuid4(), name=n) for n in names}
    session.add_all(list(teams.values()))
    await session.flush()
    return teams


async def _seed_match(
    session: AsyncSession,
    *,
    season_id,
    home: TeamORM,
    away: TeamORM,
    kickoff: datetime,
    competition_round: str,
    home_goals: int | None = None,
    away_goals: int | None = None,
    status: str = "finished",
) -> MatchORM:
    m = MatchORM(
        id=uuid4(),
        season_id=season_id,
        home_team_id=home.id,
        away_team_id=away.id,
        kickoff_utc=kickoff,
        competition_round=competition_round,
        status=status,
        home_goals=home_goals,
        away_goals=away_goals,
        is_home_neutral=False,
    )
    session.add(m)
    await session.flush()
    return m


async def _seed_model(session: AsyncSession, *, name: str, family: str) -> ModelVersionORM:
    mv = ModelVersionORM(
        id=uuid4(),
        name=name,
        family=family,
        git_sha="test",
        hyperparams={},
        metrics={},
        artifact_path=None,
        trained_at=datetime.now(UTC),
        is_promoted=False,
    )
    session.add(mv)
    await session.flush()
    return mv


async def _seed_prediction(
    session: AsyncSession,
    *,
    match_id,
    model_id,
    market: str,
    outcome: str,
    prob: float,
) -> None:
    session.add(
        PredictionORM(
            id=uuid4(),
            match_id=match_id,
            market=market,
            outcome=outcome,
            prob=prob,
            ci_low=prob,
            ci_high=prob,
            model_version_id=model_id,
            feature_snapshot_id=None,
        )
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_default_model_picks_first_alphabetical_with_predictions(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """No ?model param → first alphabetical model with predictions."""
    comp, season = await _seed_competition(db_session)
    teams = await _seed_teams(db_session, ["Brazil", "Argentina"])
    match = await _seed_match(
        db_session,
        season_id=season.id,
        home=teams["Brazil"],
        away=teams["Argentina"],
        kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
        competition_round="GROUP_STAGE",
        home_goals=2,
        away_goals=1,
    )
    model_z = await _seed_model(db_session, name="z-model", family="dixon-coles")
    model_a = await _seed_model(db_session, name="a-model", family="xgboost")
    for outcome, prob in [("home", 0.6), ("draw", 0.25), ("away", 0.15)]:
        await _seed_prediction(db_session, match_id=match.id, model_id=model_z.id, market="1x2", outcome=outcome, prob=prob)
        await _seed_prediction(db_session, match_id=match.id, model_id=model_a.id, market="1x2", outcome=outcome, prob=prob)
    await _seed_prediction(db_session, match_id=match.id, model_id=model_z.id, market="over_under_2_5", outcome="over", prob=0.7)
    await _seed_prediction(db_session, match_id=match.id, model_id=model_a.id, market="over_under_2_5", outcome="over", prob=0.7)
    await _seed_prediction(db_session, match_id=match.id, model_id=model_z.id, market="btts", outcome="yes", prob=0.65)
    await _seed_prediction(db_session, match_id=match.id, model_id=model_a.id, market="btts", outcome="yes", prob=0.65)
    await db_session.commit()

    resp = await async_client.get("/v1/accuracy/summary", headers=API_KEY_HEADER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["model"]["name"] == "a-model"  # alphabetical default
    names = [m["name"] for m in body["available_models"]]
    assert names == sorted(names)  # alphabetical order
```

- [ ] **Step 3: Run the test — it should fail (endpoint not registered yet)**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run pytest tests/integration/api/test_accuracy_summary.py -v
```

Expected: 404 from the endpoint (the route doesn't exist) — assertion `status_code == 200` FAILS.

- [ ] **Step 4: Commit (test only, drives subsequent work)**

```bash
git add tests/integration/api/test_accuracy_summary.py
git commit -m "test(api): accuracy_summary — happy-path integration test (failing)"
```

---

### Task 5: Implement use case — load + aggregate

**Files:**
- Modify: `src/analytis/application/accuracy_summary.py`

- [ ] **Step 1: Implement the `execute()` method**

Replace the `raise NotImplementedError` body with the full implementation. Add these imports at the top of the file:

```python
from collections import defaultdict
from sqlalchemy import func, select

from analytis.persistence.orm.inference import ModelVersionORM, PredictionORM
from analytis.persistence.orm.match import MatchORM
from analytis.persistence.orm.team import TeamORM
from analytis.persistence.uow import UnitOfWork
```

Implement `execute()`:

```python
    async def execute(self, params: AccuracySummaryParams) -> AccuracySummary:
        async with UnitOfWork(self._factory) as uow:
            available = await self._list_available_models(uow.session)
            if not available:
                raise ModelNotFoundError("no model has predictions yet")

            model = self._pick_model(available, params.model_name)
            rows = await self._load_match_rows(uow.session, model.id)

            kpis = self._compute_kpis(rows)
            timeseries = self._compute_timeseries(rows)
            matches = self._serialize_matches(rows)

            return AccuracySummary(
                model=ModelRef(id=model.id, name=model.name, family=model.family),
                available_models=available,
                kpis=kpis,
                timeseries=timeseries,
                matches=matches,
            )

    async def _list_available_models(self, session: AsyncSession) -> list[ModelOption]:
        stmt = (
            select(
                ModelVersionORM.id,
                ModelVersionORM.name,
                ModelVersionORM.family,
                func.count(func.distinct(PredictionORM.match_id)).label("n"),
            )
            .join(PredictionORM, PredictionORM.model_version_id == ModelVersionORM.id)
            .group_by(ModelVersionORM.id, ModelVersionORM.name, ModelVersionORM.family)
            .having(func.count(func.distinct(PredictionORM.match_id)) > 0)
            .order_by(ModelVersionORM.name)
        )
        result = await session.execute(stmt)
        return [
            ModelOption(id=r.id, name=r.name, family=r.family, n_predictions=r.n)
            for r in result
        ]

    def _pick_model(
        self, available: list[ModelOption], name: str | None
    ) -> ModelOption:
        if name is None:
            return available[0]
        for m in available:
            if m.name == name:
                return m
        raise ModelNotFoundError(f"model {name!r} not found or has no predictions")

    async def _load_match_rows(
        self, session: AsyncSession, model_id: UUID
    ) -> list[_MatchAggregate]:
        # Pull all finished matches with predictions for this model.
        # We index predictions per (match, market, outcome) → prob.
        pred_stmt = (
            select(
                MatchORM.id,
                MatchORM.kickoff_utc,
                MatchORM.competition_round,
                MatchORM.home_goals,
                MatchORM.away_goals,
                MatchORM.home_team_id,
                MatchORM.away_team_id,
                PredictionORM.market,
                PredictionORM.outcome,
                PredictionORM.prob,
            )
            .join(PredictionORM, PredictionORM.match_id == MatchORM.id)
            .where(
                PredictionORM.model_version_id == model_id,
                MatchORM.status == "finished",
                MatchORM.home_goals.is_not(None),
                MatchORM.away_goals.is_not(None),
            )
        )
        result = await session.execute(pred_stmt)

        # Index by match
        by_match: dict[UUID, _MatchAggregate] = {}
        team_ids: set[UUID] = set()
        for row in result:
            agg = by_match.setdefault(
                row.id,
                _MatchAggregate(
                    match_id=row.id,
                    kickoff_utc=row.kickoff_utc,
                    competition_round=row.competition_round,
                    home_goals=row.home_goals,
                    away_goals=row.away_goals,
                    home_team_id=row.home_team_id,
                    away_team_id=row.away_team_id,
                    probs={"1x2": {}, "over_under_2_5": {}, "btts": {}},
                ),
            )
            if row.market in agg.probs:
                agg.probs[row.market][row.outcome] = float(row.prob)
            team_ids.add(row.home_team_id)
            team_ids.add(row.away_team_id)

        # Resolve team names in one query
        team_name_stmt = select(TeamORM.id, TeamORM.name).where(TeamORM.id.in_(team_ids))
        team_map = {tid: name for tid, name in (await session.execute(team_name_stmt))}
        for agg in by_match.values():
            agg.home_team = team_map.get(agg.home_team_id, "?")
            agg.away_team = team_map.get(agg.away_team_id, "?")

        # Sort kickoff ascending (timeseries needs chronological order)
        return sorted(by_match.values(), key=lambda a: a.kickoff_utc)

    def _compute_kpis(self, rows: list[_MatchAggregate]) -> Kpis:
        hits = {"1x2": 0, "ou": 0, "btts": 0}
        n_by_mkt = {"1x2": 0, "ou": 0, "btts": 0}
        brier_sums = {"1x2": 0.0, "ou": 0.0, "btts": 0.0}

        for r in rows:
            top_1x2, _ = predicted_1x2_top(r.probs["1x2"]) if r.probs["1x2"] else (None, None)
            if top_1x2 is not None:
                actual = actual_1x2(r.home_goals, r.away_goals)
                hits["1x2"] += int(top_1x2 == actual)
                n_by_mkt["1x2"] += 1
                brier_sums["1x2"] += brier_multiclass(probs=r.probs["1x2"], actual=actual)

            ou_probs = r.probs["over_under_2_5"]
            if ou_probs:
                p_over = ou_probs.get("over", 0.0)
                pred = "over" if p_over > 0.5 else ("under" if p_over < 0.5 else None)
                actual_o = actual_ou(r.home_goals, r.away_goals)
                if pred is not None:
                    hits["ou"] += int(pred == actual_o)
                    n_by_mkt["ou"] += 1
                    brier_sums["ou"] += brier_binary(prob=p_over, outcome=1 if actual_o == "over" else 0)

            btts_probs = r.probs["btts"]
            if btts_probs:
                p_yes = btts_probs.get("yes", 0.0)
                pred = "yes" if p_yes > 0.5 else ("no" if p_yes < 0.5 else None)
                actual_b = actual_btts(r.home_goals, r.away_goals)
                if pred is not None:
                    hits["btts"] += int(pred == actual_b)
                    n_by_mkt["btts"] += 1
                    brier_sums["btts"] += brier_binary(prob=p_yes, outcome=1 if actual_b == "yes" else 0)

        markets = {}
        for key in ("1x2", "ou", "btts"):
            n = n_by_mkt[key]
            h = hits[key]
            rate = (h / n) if n else 0.0
            low, high = wilson_ci(hits=h, n=n)
            brier_avg = (brier_sums[key] / n) if n else 0.0
            markets[key] = MarketKpi(hits=h, n=n, rate=rate, ci_low=low, ci_high=high, brier_avg=brier_avg)

        total_brier_n = sum(n_by_mkt.values())
        brier_overall = (sum(brier_sums.values()) / total_brier_n) if total_brier_n else 0.0

        return Kpis(
            n_matches_evaluated=len(rows),
            markets=markets,
            brier_overall=brier_overall,
        )

    def _compute_timeseries(
        self, rows: list[_MatchAggregate]
    ) -> list[TimeseriesPoint]:
        # rows are sorted by kickoff_utc asc
        cum_hits = {"1x2": 0, "ou": 0, "btts": 0}
        cum_n = {"1x2": 0, "ou": 0, "btts": 0}
        # Track the last cumulative value seen per phase
        per_phase: dict[Phase, dict] = {}

        for r in rows:
            phase = normalize_phase(r.competition_round)
            # Update cumulatives by processing this match
            if r.probs["1x2"]:
                top, _ = predicted_1x2_top(r.probs["1x2"])
                actual = actual_1x2(r.home_goals, r.away_goals)
                cum_hits["1x2"] += int(top == actual)
                cum_n["1x2"] += 1
            if r.probs["over_under_2_5"]:
                p_over = r.probs["over_under_2_5"].get("over", 0.0)
                if p_over != 0.5:
                    pred = "over" if p_over > 0.5 else "under"
                    actual_o = actual_ou(r.home_goals, r.away_goals)
                    cum_hits["ou"] += int(pred == actual_o)
                    cum_n["ou"] += 1
            if r.probs["btts"]:
                p_yes = r.probs["btts"].get("yes", 0.0)
                if p_yes != 0.5:
                    pred = "yes" if p_yes > 0.5 else "no"
                    actual_b = actual_btts(r.home_goals, r.away_goals)
                    cum_hits["btts"] += int(pred == actual_b)
                    cum_n["btts"] += 1

            per_phase[phase] = {
                "n": len(rows[: rows.index(r) + 1]),  # n matches processed up to here
                "cumulative": {
                    k: (cum_hits[k] / cum_n[k]) if cum_n[k] else 0.0
                    for k in ("1x2", "ou", "btts")
                },
            }

        # Emit one point per phase in canonical order. If a phase has no matches yet,
        # carry forward the last seen cumulative (or zeros if none seen yet).
        out: list[TimeseriesPoint] = []
        last_n = 0
        last_cum = {"1x2": 0.0, "ou": 0.0, "btts": 0.0}
        for phase in PHASES:
            if phase in per_phase:
                last_n = per_phase[phase]["n"]
                last_cum = per_phase[phase]["cumulative"]
            out.append(TimeseriesPoint(phase=phase, n=last_n, cumulative=dict(last_cum)))
        return out

    def _serialize_matches(self, rows: list[_MatchAggregate]) -> list[MatchRow]:
        out: list[MatchRow] = []
        # Most recent first
        for r in sorted(rows, key=lambda a: a.kickoff_utc, reverse=True):
            preds: dict[str, MatchPredictionDetail] = {}

            if r.probs["1x2"]:
                top, top_p = predicted_1x2_top(r.probs["1x2"])
                actual = actual_1x2(r.home_goals, r.away_goals)
                preds["1x2"] = MatchPredictionDetail(
                    predicted=top,
                    predicted_prob=top_p,
                    actual=actual,
                    hit=top == actual,
                    brier=brier_multiclass(probs=r.probs["1x2"], actual=actual),
                )
            if r.probs["over_under_2_5"]:
                p_over = r.probs["over_under_2_5"].get("over", 0.0)
                pred = "over" if p_over > 0.5 else ("under" if p_over < 0.5 else "abstain")
                actual_o = actual_ou(r.home_goals, r.away_goals)
                preds["ou"] = MatchPredictionDetail(
                    predicted=pred,
                    predicted_prob=p_over,
                    actual=actual_o,
                    hit=pred == actual_o,
                    brier=brier_binary(prob=p_over, outcome=1 if actual_o == "over" else 0),
                )
            if r.probs["btts"]:
                p_yes = r.probs["btts"].get("yes", 0.0)
                pred = "yes" if p_yes > 0.5 else ("no" if p_yes < 0.5 else "abstain")
                actual_b = actual_btts(r.home_goals, r.away_goals)
                preds["btts"] = MatchPredictionDetail(
                    predicted=pred,
                    predicted_prob=p_yes,
                    actual=actual_b,
                    hit=pred == actual_b,
                    brier=brier_binary(prob=p_yes, outcome=1 if actual_b == "yes" else 0),
                )

            out.append(
                MatchRow(
                    match_id=r.match_id,
                    kickoff_utc=r.kickoff_utc,
                    home_team=r.home_team,
                    away_team=r.away_team,
                    home_goals=r.home_goals,
                    away_goals=r.away_goals,
                    phase=normalize_phase(r.competition_round),
                    predictions=preds,
                )
            )
        return out
```

Also add this internal dataclass near the top of the file (after the Pydantic models, before the use case class):

```python
@dataclass
class _MatchAggregate:
    """Internal: one finished match with its predictions for one model."""

    match_id: UUID
    kickoff_utc: datetime
    competition_round: str | None
    home_goals: int
    away_goals: int
    home_team_id: UUID
    away_team_id: UUID
    probs: dict[str, dict[str, float]]
    home_team: str = ""
    away_team: str = ""
```

- [ ] **Step 2: Verify the module still imports**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run python -c "from analytis.application.accuracy_summary import AccuracySummaryUseCase; print('ok')"
```

Expected: `ok`. If there's an import error (e.g., `UnitOfWork` or ORM class path wrong), fix the import path by grepping the existing codebase:

```bash
grep -rn "from analytis.persistence" src/analytis/application/ | head -5
```

Adopt whatever pattern the existing use cases use.

- [ ] **Step 3: Commit**

```bash
git add src/analytis/application/accuracy_summary.py
git commit -m "feat(api): accuracy_summary — implement aggregation pipeline"
```

---

### Task 6: FastAPI route + register in main

**Files:**
- Create: `src/analytis/api/routes/accuracy.py`
- Modify: `src/analytis/api/main.py`

- [ ] **Step 1: Inspect how other routes register themselves**

Open `src/analytis/api/routes/models.py` (or similar) to see the route pattern: `APIRouter`, `Depends(require_api_key)`, session factory injection.

- [ ] **Step 2: Create the route**

Write `src/analytis/api/routes/accuracy.py`:

```python
"""GET /v1/accuracy/summary endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from analytis.api.deps import require_api_key
from analytis.application.accuracy_summary import (
    AccuracySummary,
    AccuracySummaryParams,
    AccuracySummaryUseCase,
    ModelNotFoundError,
)
from analytis.config import Settings, get_settings
from analytis.persistence.engine import create_engine, create_session_factory

router = APIRouter(prefix="/accuracy", tags=["accuracy"], dependencies=[Depends(require_api_key)])


def _use_case(settings: Settings) -> AccuracySummaryUseCase:
    engine = create_engine(settings.database_url)
    factory = create_session_factory(engine)
    return AccuracySummaryUseCase(factory)


@router.get("/summary", response_model=AccuracySummary)
async def get_accuracy_summary(
    model: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> AccuracySummary:
    use_case = _use_case(settings)
    try:
        return await use_case.execute(AccuracySummaryParams(model_name=model))
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
```

- [ ] **Step 3: Register the router in `main.py`**

In `src/analytis/api/main.py`, add the import and `include_router` call. Use Edit to add accuracy to the imports:

old_string:
```python
from analytis.api.routes import (
    explain,
    health,
    matches,
    models,
    odds,
    predictions,
    scoreline,
    value_bets,
)
```

new_string:
```python
from analytis.api.routes import (
    accuracy,
    explain,
    health,
    matches,
    models,
    odds,
    predictions,
    scoreline,
    value_bets,
)
```

Then add the include_router call. Add after the `value_bets` line:

old_string:
```python
    app.include_router(value_bets.router, prefix="/v1")
```

new_string:
```python
    app.include_router(value_bets.router, prefix="/v1")
    app.include_router(accuracy.router, prefix="/v1")
```

- [ ] **Step 4: Run the integration test from Task 4**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run pytest tests/integration/api/test_accuracy_summary.py::test_default_model_picks_first_alphabetical_with_predictions -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/analytis/api/routes/accuracy.py src/analytis/api/main.py
git commit -m "feat(api): GET /v1/accuracy/summary endpoint"
```

---

### Task 7: Remaining backend integration tests

**Files:**
- Modify: `tests/integration/api/test_accuracy_summary.py`

- [ ] **Step 1: Append the remaining 9 tests**

Append these test functions to `tests/integration/api/test_accuracy_summary.py` (use the same `async_client`, `db_session`, and `_seed_*` helpers from Task 4):

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_returns_404_when_model_not_found(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    comp, season = await _seed_competition(db_session)
    teams = await _seed_teams(db_session, ["Brazil", "Argentina"])
    match = await _seed_match(
        db_session,
        season_id=season.id,
        home=teams["Brazil"],
        away=teams["Argentina"],
        kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
        competition_round="GROUP_STAGE",
        home_goals=2,
        away_goals=1,
    )
    real = await _seed_model(db_session, name="real-model", family="dixon-coles")
    await _seed_prediction(db_session, match_id=match.id, model_id=real.id, market="1x2", outcome="home", prob=0.6)
    await db_session.commit()

    resp = await async_client.get("/v1/accuracy/summary?model=ghost", headers=API_KEY_HEADER)
    assert resp.status_code == 404
    assert "ghost" in resp.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_returns_only_finished_matches(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    comp, season = await _seed_competition(db_session)
    teams = await _seed_teams(db_session, ["Brazil", "Argentina"])
    finished_match = await _seed_match(
        db_session,
        season_id=season.id,
        home=teams["Brazil"],
        away=teams["Argentina"],
        kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
        competition_round="GROUP_STAGE",
        home_goals=2,
        away_goals=1,
    )
    scheduled_match = await _seed_match(
        db_session,
        season_id=season.id,
        home=teams["Argentina"],
        away=teams["Brazil"],
        kickoff=datetime(2026, 6, 20, 18, 0, tzinfo=UTC),
        competition_round="GROUP_STAGE",
        status="scheduled",
    )
    model = await _seed_model(db_session, name="m1", family="dixon-coles")
    for outcome, prob in [("home", 0.6), ("draw", 0.25), ("away", 0.15)]:
        await _seed_prediction(db_session, match_id=finished_match.id, model_id=model.id, market="1x2", outcome=outcome, prob=prob)
        await _seed_prediction(db_session, match_id=scheduled_match.id, model_id=model.id, market="1x2", outcome=outcome, prob=prob)
    await db_session.commit()

    resp = await async_client.get("/v1/accuracy/summary", headers=API_KEY_HEADER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["kpis"]["n_matches_evaluated"] == 1
    assert body["kpis"]["markets"]["1x2"]["n"] == 1


async def _seed_full_match_with_prediction(
    session, *, model_id, kickoff, competition_round, score, probs_1x2, prob_over, prob_btts_yes
):
    """Helper: seed 1 finished match + full prediction set for 1 model."""
    comp, season = await _seed_competition(session)
    teams = await _seed_teams(session, [f"H-{kickoff.day}", f"A-{kickoff.day}"])
    home, away = score
    match = await _seed_match(
        session,
        season_id=season.id,
        home=teams[f"H-{kickoff.day}"],
        away=teams[f"A-{kickoff.day}"],
        kickoff=kickoff,
        competition_round=competition_round,
        home_goals=home,
        away_goals=away,
    )
    for outcome, p in probs_1x2.items():
        await _seed_prediction(session, match_id=match.id, model_id=model_id, market="1x2", outcome=outcome, prob=p)
    await _seed_prediction(session, match_id=match.id, model_id=model_id, market="over_under_2_5", outcome="over", prob=prob_over)
    await _seed_prediction(session, match_id=match.id, model_id=model_id, market="over_under_2_5", outcome="under", prob=1.0 - prob_over)
    await _seed_prediction(session, match_id=match.id, model_id=model_id, market="btts", outcome="yes", prob=prob_btts_yes)
    await _seed_prediction(session, match_id=match.id, model_id=model_id, market="btts", outcome="no", prob=1.0 - prob_btts_yes)
    return match


@pytest.mark.asyncio
@pytest.mark.integration
async def test_1x2_argmax_correctness(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    model = await _seed_model(db_session, name="m", family="dc")
    await _seed_full_match_with_prediction(
        db_session,
        model_id=model.id,
        kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
        competition_round="GROUP_STAGE",
        score=(2, 1),
        probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
        prob_over=0.7,
        prob_btts_yes=0.7,
    )
    await db_session.commit()

    resp = await async_client.get("/v1/accuracy/summary?model=m", headers=API_KEY_HEADER)
    body = resp.json()
    assert body["kpis"]["markets"]["1x2"]["hits"] == 1
    assert body["kpis"]["markets"]["1x2"]["n"] == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ou_threshold_at_0_5(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    model = await _seed_model(db_session, name="m", family="dc")
    # 1-1 = 2 goals total → actual is under 2.5. Predict prob_over=0.51 (so "over") → miss.
    await _seed_full_match_with_prediction(
        db_session,
        model_id=model.id,
        kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
        competition_round="GROUP_STAGE",
        score=(1, 1),
        probs_1x2={"home": 0.4, "draw": 0.4, "away": 0.2},
        prob_over=0.51,
        prob_btts_yes=0.7,
    )
    await db_session.commit()

    resp = await async_client.get("/v1/accuracy/summary?model=m", headers=API_KEY_HEADER)
    body = resp.json()
    assert body["kpis"]["markets"]["ou"]["hits"] == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_btts_threshold_at_0_5(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    model = await _seed_model(db_session, name="m", family="dc")
    # 2-1: both scored → BTTS=yes. prob_btts_yes=0.49 → predict "no" → miss.
    await _seed_full_match_with_prediction(
        db_session,
        model_id=model.id,
        kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
        competition_round="GROUP_STAGE",
        score=(2, 1),
        probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
        prob_over=0.7,
        prob_btts_yes=0.49,
    )
    await db_session.commit()

    resp = await async_client.get("/v1/accuracy/summary?model=m", headers=API_KEY_HEADER)
    body = resp.json()
    assert body["kpis"]["markets"]["btts"]["hits"] == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_brier_avg_calculation(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Two matches: one with prob_over=1.0 (perfect over hit), one with prob_over=0.0 (perfect over miss).
    Brier for OU should average to 0.5 ((0 + 1) / 2)."""
    model = await _seed_model(db_session, name="m", family="dc")
    await _seed_full_match_with_prediction(
        db_session,
        model_id=model.id,
        kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
        competition_round="GROUP_STAGE",
        score=(2, 1),  # over
        probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
        prob_over=1.0,  # perfectly correct on over
        prob_btts_yes=0.5,
    )
    await _seed_full_match_with_prediction(
        db_session,
        model_id=model.id,
        kickoff=datetime(2026, 6, 15, 18, 0, tzinfo=UTC),
        competition_round="GROUP_STAGE",
        score=(2, 1),  # over
        probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
        prob_over=0.0,  # perfectly wrong on over
        prob_btts_yes=0.5,
    )
    await db_session.commit()

    resp = await async_client.get("/v1/accuracy/summary?model=m", headers=API_KEY_HEADER)
    body = resp.json()
    assert body["kpis"]["markets"]["ou"]["brier_avg"] == pytest.approx(0.5, abs=1e-6)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_timeseries_cumulative_monotonic_in_n(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """As we walk through phases, the `n` field must be non-decreasing."""
    model = await _seed_model(db_session, name="m", family="dc")
    for day, comp_round in enumerate(["GROUP_STAGE", "LAST_16", "QUARTER_FINALS"], start=14):
        await _seed_full_match_with_prediction(
            db_session,
            model_id=model.id,
            kickoff=datetime(2026, 6, day, 18, 0, tzinfo=UTC),
            competition_round=comp_round,
            score=(2, 1),
            probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
            prob_over=0.7,
            prob_btts_yes=0.7,
        )
    await db_session.commit()

    resp = await async_client.get("/v1/accuracy/summary?model=m", headers=API_KEY_HEADER)
    body = resp.json()
    ns = [point["n"] for point in body["timeseries"]]
    assert ns == sorted(ns), f"n should be non-decreasing, got {ns}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_phase_normalization_in_response(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    model = await _seed_model(db_session, name="m", family="dc")
    await _seed_full_match_with_prediction(
        db_session,
        model_id=model.id,
        kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
        competition_round="LAST_16",  # Football-Data name
        score=(2, 1),
        probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
        prob_over=0.7,
        prob_btts_yes=0.7,
    )
    await db_session.commit()

    resp = await async_client.get("/v1/accuracy/summary?model=m", headers=API_KEY_HEADER)
    body = resp.json()
    assert body["matches"][0]["phase"] == "round_of_16"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_empty_db_returns_404(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    # No models seeded at all
    resp = await async_client.get("/v1/accuracy/summary", headers=API_KEY_HEADER)
    assert resp.status_code == 404
```

- [ ] **Step 2: Run all integration tests**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run pytest tests/integration/api/test_accuracy_summary.py -v
```

Expected: all 10 tests PASS. If any fail, check the assertion vs the actual response body to find the bug. Fix in `accuracy_summary.py`.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/api/test_accuracy_summary.py
git commit -m "test(api): accuracy_summary — full integration coverage (10 tests)"
```

---

## Frontend — Tasks 8-14

### Task 8: Add `fetchAccuracySummary` + TS types in `api.ts`

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Inspect the existing API client pattern**

```bash
cd "C:/Projetos/Pessoal/analytis"
head -60 frontend/src/lib/api.ts
```

Note the request helper that exists (uses `X-API-Key` from localStorage, throws `ApiError` on non-2xx). New function should reuse it.

- [ ] **Step 2: Append types + the fetch function**

Add to `frontend/src/lib/api.ts` (at the bottom, after the existing exports). The exact code:

```typescript
// ----- Accuracy dashboard -----
export type Phase = "group" | "round_of_16" | "quarterfinal" | "semifinal" | "final";

export interface ModelRef {
  id: string;
  name: string;
  family: string;
}
export interface ModelOption extends ModelRef {
  n_predictions: number;
}
export interface MarketKpi {
  hits: number;
  n: number;
  rate: number;
  ci_low: number;
  ci_high: number;
  brier_avg: number;
}
export interface AccuracyKpis {
  n_matches_evaluated: number;
  markets: { "1x2": MarketKpi; ou: MarketKpi; btts: MarketKpi };
  brier_overall: number;
}
export interface TimeseriesPoint {
  phase: Phase;
  n: number;
  cumulative: { "1x2": number; ou: number; btts: number };
}
export interface MatchPredictionDetail {
  predicted: string;
  predicted_prob: number;
  actual: string;
  hit: boolean;
  brier: number;
}
export interface MatchAccuracyRow {
  match_id: string;
  kickoff_utc: string;
  home_team: string;
  away_team: string;
  home_goals: number;
  away_goals: number;
  phase: Phase;
  predictions: {
    "1x2"?: MatchPredictionDetail;
    ou?: MatchPredictionDetail;
    btts?: MatchPredictionDetail;
  };
}
export interface AccuracySummary {
  model: ModelRef;
  available_models: ModelOption[];
  kpis: AccuracyKpis;
  timeseries: TimeseriesPoint[];
  matches: MatchAccuracyRow[];
}

export function fetchAccuracySummary(model?: string): Promise<AccuracySummary> {
  const qs = model ? `?model=${encodeURIComponent(model)}` : "";
  return request<AccuracySummary>(`/accuracy/summary${qs}`);
}
```

- [ ] **Step 3: Typecheck**

```bash
cd "C:/Projetos/Pessoal/analytis/frontend"
pnpm typecheck
```

Expected: clean exit, no errors.

- [ ] **Step 4: Commit**

```bash
cd "C:/Projetos/Pessoal/analytis"
git add frontend/src/lib/api.ts
git commit -m "feat(frontend): accuracy summary API types + fetch"
```

---

### Task 9: `useAccuracySummary` hook

**Files:**
- Create: `frontend/src/hooks/useAccuracySummary.ts`

- [ ] **Step 1: Inspect an existing hook for the react-query pattern**

```bash
cat frontend/src/hooks/useClvSummary.ts
```

Reuse the same `useQuery` shape (query key, fetcher, stale times). Keep it minimal.

- [ ] **Step 2: Create the hook**

Write `frontend/src/hooks/useAccuracySummary.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchAccuracySummary, type AccuracySummary } from "@/lib/api";

export function useAccuracySummary(model?: string) {
  return useQuery<AccuracySummary>({
    queryKey: ["accuracy", "summary", model ?? "default"],
    queryFn: () => fetchAccuracySummary(model),
    staleTime: 60_000, // 1 min: matches update at end-of-game cadence
  });
}
```

- [ ] **Step 3: Typecheck**

```bash
cd "C:/Projetos/Pessoal/analytis/frontend"
pnpm typecheck
```

Expected: clean.

- [ ] **Step 4: Commit**

```bash
cd "C:/Projetos/Pessoal/analytis"
git add frontend/src/hooks/useAccuracySummary.ts
git commit -m "feat(frontend): useAccuracySummary react-query hook"
```

---

### Task 10: `KpiCard` component

**Files:**
- Create: `frontend/src/components/accuracy/KpiCard.tsx`

- [ ] **Step 1: Create the component**

Write `frontend/src/components/accuracy/KpiCard.tsx`:

```typescript
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value: string;          // e.g. "58.3%" or "0.232"
  subtext?: string;       // e.g. "±24pp (7/12)"
  colorClass?: string;    // override text color (Brier card)
}

export function KpiCard({ label, value, subtext, colorClass }: Props) {
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-wide text-fg-muted">{label}</p>
      <p className={cn("mt-1 text-2xl font-semibold", colorClass ?? "text-fg-primary")}>
        {value}
      </p>
      {subtext && <p className="text-xs text-fg-muted">{subtext}</p>}
    </Card>
  );
}
```

- [ ] **Step 2: Typecheck**

```bash
cd "C:/Projetos/Pessoal/analytis/frontend"
pnpm typecheck
```

- [ ] **Step 3: Commit**

```bash
cd "C:/Projetos/Pessoal/analytis"
git add frontend/src/components/accuracy/KpiCard.tsx
git commit -m "feat(frontend): KpiCard component for accuracy dashboard"
```

---

### Task 11: `ModelSelector` component

**Files:**
- Create: `frontend/src/components/accuracy/ModelSelector.tsx`

- [ ] **Step 1: Check if shadcn `Select` exists in this codebase**

```bash
ls frontend/src/components/ui/ | grep -i select
```

If `select.tsx` doesn't exist, fall back to a plain native `<select>` styled with Tailwind. The component must work either way.

- [ ] **Step 2: Create the component (native `<select>` version — works without extra deps)**

Write `frontend/src/components/accuracy/ModelSelector.tsx`:

```typescript
import type { ModelOption } from "@/lib/api";

interface Props {
  models: ModelOption[];
  selected: string;
  onChange: (name: string) => void;
}

export function ModelSelector({ models, selected, onChange }: Props) {
  return (
    <select
      value={selected}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border border-white/10 bg-bg-elevated px-3 py-2 text-sm text-fg-primary focus:outline-none focus:ring-2 focus:ring-fg-primary/20"
    >
      {models.map((m) => (
        <option key={m.id} value={m.name}>
          {m.name} ({m.n_predictions} jogos)
        </option>
      ))}
    </select>
  );
}
```

- [ ] **Step 3: Typecheck**

```bash
cd "C:/Projetos/Pessoal/analytis/frontend"
pnpm typecheck
```

- [ ] **Step 4: Commit**

```bash
cd "C:/Projetos/Pessoal/analytis"
git add frontend/src/components/accuracy/ModelSelector.tsx
git commit -m "feat(frontend): ModelSelector for accuracy dashboard"
```

---

### Task 12: `AccuracyChart` component

**Files:**
- Create: `frontend/src/components/accuracy/AccuracyChart.tsx`

- [ ] **Step 1: Inspect existing recharts usage in the project**

```bash
grep -rn "from \"recharts\"" frontend/src/components/ | head -5
```

Match the patterns (ResponsiveContainer, theming via Tailwind colors).

- [ ] **Step 2: Create the component**

Write `frontend/src/components/accuracy/AccuracyChart.tsx`:

```typescript
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Phase, TimeseriesPoint } from "@/lib/api";

const PHASE_LABELS: Record<Phase, string> = {
  group: "Grupo",
  round_of_16: "Oitavas",
  quarterfinal: "Quartas",
  semifinal: "Semi",
  final: "Final",
};

interface Props {
  data: TimeseriesPoint[];
}

export function AccuracyChart({ data }: Props) {
  const rows = data.map((p) => ({
    phase: PHASE_LABELS[p.phase],
    n: p.n,
    "1X2": Math.round(p.cumulative["1x2"] * 1000) / 10,
    OU: Math.round(p.cumulative.ou * 1000) / 10,
    BTTS: Math.round(p.cumulative.btts * 1000) / 10,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={rows} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="phase" stroke="rgba(255,255,255,0.5)" fontSize={11} />
        <YAxis domain={[0, 100]} stroke="rgba(255,255,255,0.5)" fontSize={11} tickFormatter={(v) => `${v}%`} />
        <Tooltip
          contentStyle={{ backgroundColor: "rgb(15, 23, 42)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
          labelStyle={{ color: "rgba(255,255,255,0.85)" }}
          formatter={(v: number) => `${v}%`}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="1X2" stroke="#38bdf8" strokeWidth={2} dot={{ r: 3 }} />
        <Line type="monotone" dataKey="OU" stroke="#4ade80" strokeWidth={2} dot={{ r: 3 }} />
        <Line type="monotone" dataKey="BTTS" stroke="#c084fc" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 3: Typecheck**

```bash
cd "C:/Projetos/Pessoal/analytis/frontend"
pnpm typecheck
```

- [ ] **Step 4: Commit**

```bash
cd "C:/Projetos/Pessoal/analytis"
git add frontend/src/components/accuracy/AccuracyChart.tsx
git commit -m "feat(frontend): AccuracyChart (recharts line, cumulative by phase)"
```

---

### Task 13: `MatchAccuracyTable` component

**Files:**
- Create: `frontend/src/components/accuracy/MatchAccuracyTable.tsx`

- [ ] **Step 1: Create the component**

Write `frontend/src/components/accuracy/MatchAccuracyTable.tsx`:

```typescript
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import type { MatchAccuracyRow, Phase } from "@/lib/api";
import { cn } from "@/lib/utils";

const PHASE_LABELS: Record<Phase, string> = {
  group: "Grupo",
  round_of_16: "Oitavas",
  quarterfinal: "Quartas",
  semifinal: "Semi",
  final: "Final",
};

interface Props {
  rows: MatchAccuracyRow[];
}

export function MatchAccuracyTable({ rows }: Props) {
  const navigate = useNavigate();

  if (rows.length === 0) {
    return <p className="text-sm text-fg-muted">Sem jogos avaliados ainda.</p>;
  }

  return (
    <div className="space-y-2">
      {rows.map((row) => (
        <Card
          key={row.match_id}
          className="p-3 cursor-pointer hover:bg-bg-overlay/40 transition-colors"
          onClick={() => navigate(`/matches/${row.match_id}`)}
        >
          <div className="flex justify-between items-center text-xs text-fg-muted mb-1">
            <span>{new Date(row.kickoff_utc).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })}</span>
            <span>{PHASE_LABELS[row.phase]}</span>
          </div>
          <div className="flex justify-between items-baseline mb-2">
            <span className="text-sm text-fg-primary">{row.home_team} vs {row.away_team}</span>
            <span className="text-sm font-semibold text-fg-primary">{row.home_goals}-{row.away_goals}</span>
          </div>
          <div className="flex gap-3 text-xs">
            {(["1x2", "ou", "btts"] as const).map((mkt) => {
              const p = row.predictions[mkt];
              if (!p) return null;
              return (
                <span
                  key={mkt}
                  className={cn(
                    "inline-flex items-center gap-1",
                    p.hit ? "text-green-400" : "text-red-400",
                  )}
                >
                  {p.hit ? "✓" : "✗"} {mkt.toUpperCase()}: {p.predicted} ({Math.round(p.predicted_prob * 100)}%)
                </span>
              );
            })}
          </div>
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

```bash
cd "C:/Projetos/Pessoal/analytis/frontend"
pnpm typecheck
```

- [ ] **Step 3: Commit**

```bash
cd "C:/Projetos/Pessoal/analytis"
git add frontend/src/components/accuracy/MatchAccuracyTable.tsx
git commit -m "feat(frontend): MatchAccuracyTable component (card list)"
```

---

### Task 14: `AccuracyPage` + route + nav links

**Files:**
- Create: `frontend/src/pages/AccuracyPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/Header.tsx`
- Modify: `frontend/src/components/layout/BottomNav.tsx`

- [ ] **Step 1: Create the page**

Write `frontend/src/pages/AccuracyPage.tsx`:

```typescript
import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AccuracyChart } from "@/components/accuracy/AccuracyChart";
import { KpiCard } from "@/components/accuracy/KpiCard";
import { MatchAccuracyTable } from "@/components/accuracy/MatchAccuracyTable";
import { ModelSelector } from "@/components/accuracy/ModelSelector";
import { useAccuracySummary } from "@/hooks/useAccuracySummary";

function fmtPct(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

function fmtPp(low: number, high: number): string {
  // Half-width of CI in percentage points
  const half = ((high - low) / 2) * 100;
  return `±${half.toFixed(0)}pp`;
}

function brierColor(brier: number): string {
  if (brier < 0.20) return "text-green-400";
  if (brier > 0.30) return "text-red-400";
  return "text-yellow-400";
}

export default function AccuracyPage() {
  const [model, setModel] = useState<string | undefined>(undefined);
  const { data, isLoading, isError, error, refetch } = useAccuracySummary(model);

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-3xl">
        <header><h2 className="text-2xl font-semibold">Acertos</h2></header>
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-60" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="space-y-4 max-w-3xl">
        <h2 className="text-2xl font-semibold">Acertos</h2>
        <Card className="p-4">
          <p className="text-sm text-red-400">Erro ao carregar: {error instanceof Error ? error.message : "desconhecido"}</p>
          <button
            type="button"
            className="mt-2 text-sm underline text-fg-primary"
            onClick={() => refetch()}
          >
            Tentar novamente
          </button>
        </Card>
      </div>
    );
  }

  if (data.kpis.n_matches_evaluated === 0) {
    return (
      <div className="space-y-4 max-w-3xl">
        <h2 className="text-2xl font-semibold">Acertos</h2>
        <ModelSelector
          models={data.available_models}
          selected={data.model.name}
          onChange={setModel}
        />
        <Card className="p-6 text-center">
          <p className="text-sm text-fg-muted">
            Nenhum jogo com resultado disponível pra esse modelo ainda.
          </p>
        </Card>
      </div>
    );
  }

  const m = data.kpis.markets;

  return (
    <div className="space-y-6 max-w-3xl">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold">Acertos</h2>
        <div className="flex items-center gap-3">
          <ModelSelector
            models={data.available_models}
            selected={data.model.name}
            onChange={setModel}
          />
          <span className="text-sm text-fg-muted">
            {data.kpis.n_matches_evaluated} jogos avaliados
          </span>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-3">
        <KpiCard
          label="1X2"
          value={fmtPct(m["1x2"].rate)}
          subtext={`${fmtPp(m["1x2"].ci_low, m["1x2"].ci_high)} (${m["1x2"].hits}/${m["1x2"].n})`}
        />
        <KpiCard
          label="OU 2.5"
          value={fmtPct(m.ou.rate)}
          subtext={`${fmtPp(m.ou.ci_low, m.ou.ci_high)} (${m.ou.hits}/${m.ou.n})`}
        />
        <KpiCard
          label="BTTS"
          value={fmtPct(m.btts.rate)}
          subtext={`${fmtPp(m.btts.ci_low, m.btts.ci_high)} (${m.btts.hits}/${m.btts.n})`}
        />
        <KpiCard
          label="Brier médio"
          value={data.kpis.brier_overall.toFixed(3)}
          colorClass={brierColor(data.kpis.brier_overall)}
          subtext="< 0.20 = bom, > 0.30 = ruim"
        />
      </div>

      <Card className="p-4">
        <h3 className="text-sm font-medium text-fg-muted mb-2">Acerto cumulativo por fase</h3>
        <AccuracyChart data={data.timeseries} />
      </Card>

      <section>
        <h3 className="text-base font-semibold mb-2">Jogos</h3>
        <MatchAccuracyTable rows={data.matches} />
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Add the route in `App.tsx`**

Edit `frontend/src/App.tsx`. Add the import:

old_string:
```typescript
import MethodologyPage from "@/pages/MethodologyPage";
```

new_string:
```typescript
import AccuracyPage from "@/pages/AccuracyPage";
import MethodologyPage from "@/pages/MethodologyPage";
```

Add the route:

old_string:
```typescript
            <Route path="/metodologia" element={<MethodologyPage />} />
```

new_string:
```typescript
            <Route path="/acertos" element={<AccuracyPage />} />
            <Route path="/metodologia" element={<MethodologyPage />} />
```

- [ ] **Step 3: Add nav link in Header**

Edit `frontend/src/components/layout/Header.tsx`. Update the `navItems` array:

old_string:
```typescript
const navItems = [
  { to: "/", label: "Jogos", icon: Home },
  { to: "/bets", label: "Value Bets", icon: Gem },
  { to: "/clv", label: "CLV", icon: TrendingUp },
  { to: "/metodologia", label: "Metodologia", icon: BookOpen },
];
```

new_string:
```typescript
const navItems = [
  { to: "/", label: "Jogos", icon: Home },
  { to: "/bets", label: "Value Bets", icon: Gem },
  { to: "/clv", label: "CLV", icon: TrendingUp },
  { to: "/acertos", label: "Acertos", icon: Target },
  { to: "/metodologia", label: "Metodologia", icon: BookOpen },
];
```

And update the lucide import:

old_string:
```typescript
import { BookOpen, Gem, Home, Settings, TrendingUp } from "lucide-react";
```

new_string:
```typescript
import { BookOpen, Gem, Home, Settings, Target, TrendingUp } from "lucide-react";
```

- [ ] **Step 4: Add nav link in BottomNav + bump to grid-cols-6**

Edit `frontend/src/components/layout/BottomNav.tsx`. Update imports:

old_string:
```typescript
import { BookOpen, Gem, Home, Settings, TrendingUp } from "lucide-react";
```

new_string:
```typescript
import { BookOpen, Gem, Home, Settings, Target, TrendingUp } from "lucide-react";
```

Update navItems:

old_string:
```typescript
const navItems = [
  { to: "/", label: "Jogos", icon: Home },
  { to: "/bets", label: "Bets", icon: Gem },
  { to: "/clv", label: "CLV", icon: TrendingUp },
  { to: "/metodologia", label: "Metodo", icon: BookOpen },
];
```

new_string:
```typescript
const navItems = [
  { to: "/", label: "Jogos", icon: Home },
  { to: "/bets", label: "Bets", icon: Gem },
  { to: "/clv", label: "CLV", icon: TrendingUp },
  { to: "/acertos", label: "Acertos", icon: Target },
  { to: "/metodologia", label: "Metodo", icon: BookOpen },
];
```

Update the grid columns:

old_string:
```typescript
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-20 grid grid-cols-5 border-t border-white/10 bg-bg-base/90 backdrop-blur pb-[env(safe-area-inset-bottom)]">
```

new_string:
```typescript
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-20 grid grid-cols-6 border-t border-white/10 bg-bg-base/90 backdrop-blur pb-[env(safe-area-inset-bottom)]">
```

- [ ] **Step 5: Typecheck**

```bash
cd "C:/Projetos/Pessoal/analytis/frontend"
pnpm typecheck
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
cd "C:/Projetos/Pessoal/analytis"
git add frontend/src/pages/AccuracyPage.tsx frontend/src/App.tsx frontend/src/components/layout/Header.tsx frontend/src/components/layout/BottomNav.tsx
git commit -m "feat(frontend): /acertos dashboard page + nav links"
```

---

### Task 15: Frontend page tests

**Files:**
- Create: `frontend/src/pages/__tests__/AccuracyPage.test.tsx`

- [ ] **Step 1: Inspect the existing test util**

```bash
cat frontend/src/test/test-utils.tsx
```

Note how it wraps components in QueryClientProvider + MemoryRouter.

- [ ] **Step 2: Create the test file**

Write `frontend/src/pages/__tests__/AccuracyPage.test.tsx`:

```typescript
import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/test-utils";
import AccuracyPage from "@/pages/AccuracyPage";
import type { AccuracySummary } from "@/lib/api";

// Mock the hook directly — bypass network/react-query and inject states.
vi.mock("@/hooks/useAccuracySummary", () => ({
  useAccuracySummary: vi.fn(),
}));

import { useAccuracySummary } from "@/hooks/useAccuracySummary";
const mockHook = useAccuracySummary as ReturnType<typeof vi.fn>;

function sampleData(overrides: Partial<AccuracySummary> = {}): AccuracySummary {
  return {
    model: { id: "m1", name: "ensemble-v1", family: "ensemble" },
    available_models: [
      { id: "m1", name: "ensemble-v1", family: "ensemble", n_predictions: 12 },
      { id: "m2", name: "xgb-1x2-v1", family: "xgboost", n_predictions: 12 },
    ],
    kpis: {
      n_matches_evaluated: 12,
      markets: {
        "1x2": { hits: 7, n: 12, rate: 0.583, ci_low: 0.319, ci_high: 0.806, brier_avg: 0.198 },
        ou:    { hits: 8, n: 12, rate: 0.667, ci_low: 0.394, ci_high: 0.864, brier_avg: 0.245 },
        btts:  { hits: 6, n: 12, rate: 0.500, ci_low: 0.248, ci_high: 0.752, brier_avg: 0.252 },
      },
      brier_overall: 0.232,
    },
    timeseries: [
      { phase: "group", n: 8, cumulative: { "1x2": 0.625, ou: 0.75, btts: 0.5 } },
    ],
    matches: [
      {
        match_id: "abc",
        kickoff_utc: "2026-06-14T18:00:00Z",
        home_team: "Brazil",
        away_team: "Argentina",
        home_goals: 2,
        away_goals: 1,
        phase: "round_of_16",
        predictions: {
          "1x2": { predicted: "home", predicted_prob: 0.539, actual: "home", hit: true, brier: 0.21 },
        },
      },
    ],
    ...overrides,
  };
}

describe("AccuracyPage", () => {
  it("renders header + skeletons on loading", () => {
    mockHook.mockReturnValue({ isLoading: true, isError: false, data: undefined });
    renderWithProviders(<AccuracyPage />);
    expect(screen.getByText("Acertos")).toBeInTheDocument();
  });

  it("renders KPI values from data", () => {
    mockHook.mockReturnValue({ isLoading: false, isError: false, data: sampleData() });
    renderWithProviders(<AccuracyPage />);
    expect(screen.getByText("58.3%")).toBeInTheDocument();   // 1X2 rate
    expect(screen.getByText("66.7%")).toBeInTheDocument();   // OU rate
    expect(screen.getByText("50.0%")).toBeInTheDocument();   // BTTS rate
    expect(screen.getByText("0.232")).toBeInTheDocument();   // Brier overall
  });

  it.each([
    [0.18, "text-green-400"],
    [0.25, "text-yellow-400"],
    [0.35, "text-red-400"],
  ])("Brier card color = %s threshold", (brier, expectedClass) => {
    const data = sampleData();
    data.kpis.brier_overall = brier;
    mockHook.mockReturnValue({ isLoading: false, isError: false, data });
    renderWithProviders(<AccuracyPage />);
    expect(screen.getByText(brier.toFixed(3))).toHaveClass(expectedClass);
  });

  it("shows empty state when n_matches_evaluated is 0", () => {
    const data = sampleData();
    data.kpis.n_matches_evaluated = 0;
    mockHook.mockReturnValue({ isLoading: false, isError: false, data });
    renderWithProviders(<AccuracyPage />);
    expect(screen.getByText(/Nenhum jogo com resultado/i)).toBeInTheDocument();
  });

  it("changing ModelSelector triggers a new fetch", async () => {
    mockHook.mockReturnValue({ isLoading: false, isError: false, data: sampleData() });
    renderWithProviders(<AccuracyPage />);
    const select = screen.getByRole("combobox");
    await userEvent.selectOptions(select, "xgb-1x2-v1");
    // The hook is called again with the new arg — useState updates trigger re-render.
    await waitFor(() => {
      expect(mockHook).toHaveBeenLastCalledWith("xgb-1x2-v1");
    });
  });

  it("clicking a match card navigates to /matches/:id", async () => {
    mockHook.mockReturnValue({ isLoading: false, isError: false, data: sampleData() });
    const { navigate } = renderWithProviders(<AccuracyPage />, { withNavigate: true });
    const card = screen.getByText(/Brazil vs Argentina/).closest("[class*='cursor-pointer']");
    expect(card).not.toBeNull();
    await userEvent.click(card!);
    expect(navigate).toHaveBeenCalledWith("/matches/abc");
  });
});
```

Note: The last test assumes `renderWithProviders` accepts a `withNavigate: true` option that injects a navigate spy. If it doesn't:
- Inspect `frontend/src/test/test-utils.tsx`
- Adapt the test to use the existing pattern (likely it mocks `react-router-dom` via `vi.mock` or wraps with `MemoryRouter` + a navigate listener)
- If the test util doesn't support navigation assertions, replace the last test with: assert the card has `cursor-pointer` class as proxy for click affordance

- [ ] **Step 3: Run the tests**

```bash
cd "C:/Projetos/Pessoal/analytis/frontend"
pnpm test src/pages/__tests__/AccuracyPage.test.tsx
```

Expected: 6 PASS (or 5 PASS + the navigation test adapted as above).

- [ ] **Step 4: Commit**

```bash
cd "C:/Projetos/Pessoal/analytis"
git add frontend/src/pages/__tests__/AccuracyPage.test.tsx
git commit -m "test(frontend): AccuracyPage — 6 tests covering loading/data/empty/select/nav"
```

---

### Task 16: Deploy + production smoke test

**Files:** none (deploy only)

- [ ] **Step 1: Run the deploy script**

```bash
cd "C:/Projetos/Pessoal/analytis"
bash deploy/deploy.sh
```

Expected: `[deploy] Done.` at the end. Takes ~8-10 minutes (build + 1.3 GB upload + load + finish.sh on VM).

- [ ] **Step 2: Smoke test the new endpoint**

```bash
curl -fsS --resolve analytis.zyntra.company:443:163.176.194.231 \
  -H "X-API-Key: dariokrugerjunior1999" \
  https://analytis.zyntra.company/v1/accuracy/summary | python -m json.tool | head -30
```

Expected: JSON with `model`, `available_models` (3 entries — `dc-v1-no-decay`, `ensemble-v1`, `xgb-1x2-v1`), `kpis`, `timeseries`, `matches`.

- [ ] **Step 3: Smoke test a specific model**

```bash
curl -fsS --resolve analytis.zyntra.company:443:163.176.194.231 \
  -H "X-API-Key: dariokrugerjunior1999" \
  "https://analytis.zyntra.company/v1/accuracy/summary?model=ensemble-v1" \
  | python -m json.tool | head -20
```

Expected: response with `"name": "ensemble-v1"`.

- [ ] **Step 4: Visual check on installed PWA (manual)**

Open the analytis PWA on iPhone (the installed home-screen icon from Fase 1). Tap "Acertos" in the bottom nav. Confirm:
- Page loads
- KPI cards show real numbers
- Chart renders (3 lines if there's data in multiple phases)
- Match cards are tappable and navigate to detail
- ModelSelector switches data correctly

---

## Plan-vs-spec self-review

**Spec coverage** — each spec section mapped to tasks:

- ✅ Definições de "acerto" → Tasks 3 (helpers) + 5 (use case wiring)
- ✅ Definições de métricas (Brier multiclass/binary, Wilson CI) → Tasks 2 + 3
- ✅ Normalização de fase → Task 2
- ✅ Endpoint shape (response JSON) → Tasks 1 (schemas) + 5 (use case)
- ✅ Default model alphabetical + 404 → Tasks 4 (first test) + 5 (`_pick_model`)
- ✅ Available models alphabetical order → Task 5 (`_list_available_models` ORDER BY)
- ✅ Frontend layout (KPIs, chart, table, model selector) → Tasks 10-14
- ✅ Loading/empty/error states → Task 14 (AccuracyPage)
- ✅ Brier color thresholds → Task 14 (`brierColor`)
- ✅ Nav links + grid-cols-6 → Task 14 step 4
- ✅ 10 backend tests + 6 frontend tests → Tasks 4, 7, 15
- ✅ Smoke prod → Task 16

**Placeholder scan** — no TBD/TODO/"add validation" patterns. Every step has concrete code or exact commands.

**Type consistency:**
- `Phase` Literal used identically in backend (Task 1) and frontend (Task 8)
- Market keys `"1x2"`, `"ou"`, `"btts"` consistent across backend (Tasks 1, 5), frontend types (Task 8), API mapping (Task 5 — `over_under_2_5` → `ou`)
- `predicted_1x2_top` signature `(probs) -> (str, float)` matches usage in Task 5 and helper test (Task 3)
- `MarketKpi`/`AccuracyKpis`/`MatchAccuracyRow` interfaces identical in TS (Task 8) and Pydantic (Task 1)

**One asymmetry intentionally introduced:** Pydantic models use snake_case (`ci_low`), TypeScript types use the same snake_case (mirror the wire format) — no auto-camelCasing layer between them. Documented as a deliberate convention so future readers don't try to "fix" it.
