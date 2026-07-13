# PWA Fase 2 — Web Push Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Web Push notifications that fire 10 minutes before each Copa 2026 kickoff (with `ensemble-v1` predictions) and right after each match ends (with prediction vs result), delivered to iPhone PWAs installed via Fase 1.

**Architecture:** Service Worker registered by the SPA + backend FastAPI subscribe endpoint + Postgres tables for subscriptions and notification idempotency + Python CLI dispatcher (`analytis push dispatch`) using `pywebpush` + cron on the VM every minute. All subscriptions receive all matches (no per-match opt-in).

**Tech Stack:**
- Backend: FastAPI, async SQLAlchemy, `pywebpush` (~0.15), `py-vapid` (~1.9), Alembic
- Frontend: React 18, Service Worker API, Notification API, Push API
- Infra: cron + flock + Docker compose
- Tests: pytest (unit + integration), vitest (frontend smoke)

**Spec:** `docs/superpowers/specs/2026-06-20-pwa-fase2-webpush-design.md`

---

## File Structure

**Backend (create):**
- `migrations/versions/0005_push_notifications.py`
- `src/analytis/persistence/orm/push.py` — `PushSubscriptionORM`, `MatchNotificationORM`
- `src/analytis/domain/push.py` — `PushSubscription`, `MatchNotification` Pydantic entities
- `src/analytis/persistence/repositories/push_subscription.py`
- `src/analytis/push/__init__.py`
- `src/analytis/push/vapid.py` — VAPID config loader
- `src/analytis/push/bodies.py` — payload builders
- `src/analytis/push/dispatcher.py` — `PushDispatcher`
- `src/analytis/api/routes/push.py` — subscribe + vapid-public-key endpoints
- `src/analytis/cli/push.py` — `analytis push dispatch` + `analytis push generate-vapid-keys`
- `tests/unit/push/test_vapid.py`
- `tests/unit/push/test_bodies.py`
- `tests/integration/api/test_push_routes.py`
- `tests/integration/push/test_dispatcher.py`

**Backend (modify):**
- `pyproject.toml` — add `pywebpush`, `py-vapid` to runtime deps
- `src/analytis/config.py` — add `vapid_private_key`, `vapid_public_key`, `vapid_subject` settings
- `src/analytis/cli/app.py` — register `push` subcommand
- `src/analytis/api/main.py` — register `push.router`

**Frontend (create):**
- `frontend/public/sw.js` — service worker
- `frontend/src/lib/push.ts` — `enablePush()`, `isSubscribed()`
- `frontend/src/components/PushPrompt.tsx`

**Frontend (modify):**
- `frontend/src/App.tsx` — mount `<PushPrompt />`

**Deploy (create):**
- `deploy/cron/push-dispatcher.sh`

**Deploy (modify):**
- `deploy/finish.sh` — install push cron entry
- `deploy/.env.prod.example` — add VAPID placeholders
- `deploy/.env.prod` — receives generated VAPID keys

---

## Task 1: Add Python dependencies

**Files:**
- Modify: `pyproject.toml` (dependencies section)

- [ ] **Step 1: Add `pywebpush` and `py-vapid` to `[project.dependencies]`**

Open `pyproject.toml`. Locate the `dependencies = [...]` array under `[project]`. Add two lines (alphabetically, between existing entries):

```toml
    "py-vapid>=1.9.0",
    "pywebpush>=2.0.0",
```

- [ ] **Step 2: Run `uv sync` to update lock**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv sync
```

Expected: `uv.lock` updated with `pywebpush`, `py-vapid`, and their deps (`http-ece`, `cryptography`, etc.).

- [ ] **Step 3: Verify imports work**

```bash
uv run python -c "import pywebpush, py_vapid; print('ok')"
```

Expected: `ok`. If error, check that the packages installed correctly.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add pywebpush + py-vapid for web push notifications"
```

---

## Task 2: Settings — VAPID keys env vars

**Files:**
- Modify: `src/analytis/config.py`

- [ ] **Step 1: Add VAPID fields to `Settings`**

Open `src/analytis/config.py`. After the existing `auto_ingest_*` block, add three new fields:

```python
    vapid_private_key: SecretStr | None = None
    vapid_public_key: str | None = None
    vapid_subject: str = "mailto:admin@example.com"
```

Place them inside the `Settings` class with the other optional fields. Preserve existing indentation (4 spaces).

- [ ] **Step 2: Verify import**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run python -c "from analytis.config import get_settings; print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add src/analytis/config.py
git commit -m "feat(config): add VAPID env settings for web push"
```

---

## Task 3: Alembic migration — push_subscription + match_notification

**Files:**
- Create: `migrations/versions/0005_push_notifications.py`

- [ ] **Step 1: Create the migration file**

Use Write to create `migrations/versions/0005_push_notifications.py`:

```python
"""push notifications

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-20

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "push_subscription",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("endpoint", sa.Text(), nullable=False, unique=True),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    op.create_table(
        "match_notification",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "match_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("match.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("n_recipients", sa.Integer(), nullable=False),
        sa.CheckConstraint("kind IN ('pre', 'post')", name="match_notification_kind_check"),
        sa.UniqueConstraint("match_id", "kind", name="match_notification_unique"),
    )


def downgrade() -> None:
    op.drop_table("match_notification")
    op.drop_table("push_subscription")
```

- [ ] **Step 2: Apply migration locally**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run analytis db migrate
```

Expected: `Running upgrade 0004 -> 0005, push notifications` then `Migrated to head`.

- [ ] **Step 3: Verify tables exist**

```bash
docker exec analytis-postgres psql -U analytis -d analytis -c "\d push_subscription" 2>&1 | head -10
docker exec analytis-postgres psql -U analytis -d analytis -c "\d match_notification" 2>&1 | head -10
```

Expected: both tables described with the columns/constraints declared above.

- [ ] **Step 4: Commit**

```bash
git add migrations/versions/0005_push_notifications.py
git commit -m "feat(db): migration 0005 — push_subscription + match_notification"
```

---

## Task 4: ORM models for push

**Files:**
- Create: `src/analytis/persistence/orm/push.py`

- [ ] **Step 1: Create the ORM models**

```python
"""ORM models for push notification subsystem."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from analytis.persistence.orm.base import Base


class PushSubscriptionORM(Base):
    __tablename__ = "push_subscription"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )


class MatchNotificationORM(Base):
    __tablename__ = "match_notification"
    __table_args__ = (
        CheckConstraint("kind IN ('pre', 'post')", name="match_notification_kind_check"),
        UniqueConstraint("match_id", "kind", name="match_notification_unique"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("match.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    n_recipients: Mapped[int] = mapped_column(Integer, nullable=False)
```

- [ ] **Step 2: Verify import**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run python -c "from analytis.persistence.orm.push import PushSubscriptionORM, MatchNotificationORM; print('ok')"
```

Expected: `ok`. If import path of `Base` differs, locate it via:

```bash
grep -rn "class Base" src/analytis/persistence/orm/ | head -3
```

and adapt the import.

- [ ] **Step 3: Commit**

```bash
git add src/analytis/persistence/orm/push.py
git commit -m "feat(db): ORM models PushSubscriptionORM + MatchNotificationORM"
```

---

## Task 5: VAPID config loader + unit tests

**Files:**
- Create: `src/analytis/push/__init__.py` (empty)
- Create: `src/analytis/push/vapid.py`
- Create: `tests/unit/push/__init__.py` (empty)
- Create: `tests/unit/push/test_vapid.py`

- [ ] **Step 1: Create the empty package files**

Write `src/analytis/push/__init__.py` with content:

```python
"""Web push notification subsystem."""
```

Write `tests/unit/push/__init__.py` empty (no content needed; an empty file).

- [ ] **Step 2: Write the failing test**

Create `tests/unit/push/test_vapid.py`:

```python
import pytest

from analytis.push.vapid import VapidConfig, load_vapid_config


def test_load_vapid_config_from_settings():
    cfg = load_vapid_config(
        private_key="priv",
        public_key="pub",
        subject="mailto:test@example.com",
    )
    assert isinstance(cfg, VapidConfig)
    assert cfg.private_key == "priv"
    assert cfg.public_key == "pub"
    assert cfg.subject == "mailto:test@example.com"


def test_load_vapid_config_missing_private_raises():
    with pytest.raises(ValueError, match="VAPID private key"):
        load_vapid_config(private_key=None, public_key="pub", subject="mailto:x@y.z")


def test_load_vapid_config_missing_public_raises():
    with pytest.raises(ValueError, match="VAPID public key"):
        load_vapid_config(private_key="priv", public_key=None, subject="mailto:x@y.z")
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run pytest tests/unit/push/test_vapid.py -v
```

Expected: ImportError on `analytis.push.vapid`.

- [ ] **Step 4: Implement**

Create `src/analytis/push/vapid.py`:

```python
"""VAPID config — private/public keypair + subject for Web Push signing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VapidConfig:
    private_key: str
    public_key: str
    subject: str


def load_vapid_config(
    *,
    private_key: str | None,
    public_key: str | None,
    subject: str,
) -> VapidConfig:
    """Build VapidConfig from settings values; raise if essentials missing."""
    if not private_key:
        raise ValueError("VAPID private key missing (set ANALYTIS_VAPID_PRIVATE_KEY)")
    if not public_key:
        raise ValueError("VAPID public key missing (set ANALYTIS_VAPID_PUBLIC_KEY)")
    return VapidConfig(private_key=private_key, public_key=public_key, subject=subject)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/unit/push/test_vapid.py -v
```

Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add src/analytis/push/__init__.py src/analytis/push/vapid.py tests/unit/push/__init__.py tests/unit/push/test_vapid.py
git commit -m "feat(push): VapidConfig loader + tests"
```

---

## Task 6: Body builders + unit tests

**Files:**
- Create: `src/analytis/push/bodies.py`
- Create: `tests/unit/push/test_bodies.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/push/test_bodies.py`:

```python
from analytis.push.bodies import build_post_payload, build_pre_payload


def _fake_match(*, home="Brazil", away="Argentina", match_id="abc-uuid", home_goals=None, away_goals=None):
    return {
        "id": match_id,
        "home_team": home,
        "away_team": away,
        "home_goals": home_goals,
        "away_goals": away_goals,
    }


def _fake_probs_home_win():
    return {"home": 0.55, "draw": 0.25, "away": 0.20}


def test_build_pre_payload_home_win():
    match = _fake_match()
    payload = build_pre_payload(match, _fake_probs_home_win())
    assert "Brazil" in payload["title"]
    assert "Argentina" in payload["title"]
    assert "10 min" in payload["title"] or "10min" in payload["title"]
    assert "55" in payload["body"]
    assert payload["url"] == "/matches/abc-uuid"


def test_build_pre_payload_draw_probs():
    match = _fake_match()
    payload = build_pre_payload(match, {"home": 0.32, "draw": 0.42, "away": 0.26})
    assert "42" in payload["body"]  # draw highlighted because highest


def test_build_post_payload_correct_winner():
    match = _fake_match(home_goals=2, away_goals=1)
    payload = build_post_payload(match, _fake_probs_home_win())
    assert "2-1" in payload["title"] or "2 - 1" in payload["title"]
    assert "Brazil" in payload["title"]
    assert payload["url"] == "/matches/abc-uuid"
    # Body should indicate hit (predicted home win, actual home win)
    assert "✓" in payload["body"] or "acerto" in payload["body"].lower()


def test_build_post_payload_wrong_winner():
    match = _fake_match(home_goals=0, away_goals=2)
    payload = build_post_payload(match, _fake_probs_home_win())
    assert "✗" in payload["body"] or "errou" in payload["body"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/push/test_bodies.py -v
```

Expected: ImportError on `analytis.push.bodies`.

- [ ] **Step 3: Implement**

Create `src/analytis/push/bodies.py`:

```python
"""Build push notification payloads (title/body/url) from match + prediction data."""

from __future__ import annotations

from typing import Any


def _top_1x2(probs: dict[str, float]) -> tuple[str, float]:
    """Return (outcome, prob) of highest 1x2 probability."""
    return max(probs.items(), key=lambda kv: kv[1])


_OUTCOME_LABEL = {"home": "vitória mandante", "draw": "empate", "away": "vitória visitante"}


def build_pre_payload(match: dict[str, Any], probs_1x2: dict[str, float]) -> dict[str, str]:
    """Pre-game payload, 10 min before kickoff."""
    home = match["home_team"]
    away = match["away_team"]
    top_outcome, top_prob = _top_1x2(probs_1x2)
    pct = lambda k: f"{int(round(probs_1x2[k] * 100))}%"  # noqa: E731
    body = f"{home} {pct('home')} · empate {pct('draw')} · {away} {pct('away')}"
    return {
        "title": f"{home} × {away} em 10 min",
        "body": body,
        "url": f"/matches/{match['id']}",
    }


def build_post_payload(match: dict[str, Any], probs_1x2: dict[str, float]) -> dict[str, str]:
    """Post-game payload, right after match ends."""
    home = match["home_team"]
    away = match["away_team"]
    hg = match["home_goals"]
    ag = match["away_goals"]
    if hg is None or ag is None:
        raise ValueError("post payload requires finished match with goals")

    actual = "home" if hg > ag else ("away" if hg < ag else "draw")
    top_outcome, top_prob = _top_1x2(probs_1x2)

    marker = "✓ acerto 1X2" if top_outcome == actual else "✗ errou 1X2"
    body = (
        f"Sua previsão: {_OUTCOME_LABEL[top_outcome]} ({int(round(top_prob*100))}%) — {marker}"
    )
    return {
        "title": f"{home} {hg}-{ag} {away}",
        "body": body,
        "url": f"/matches/{match['id']}",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/push/test_bodies.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/analytis/push/bodies.py tests/unit/push/test_bodies.py
git commit -m "feat(push): notification body builders + tests"
```

---

## Task 7: PushSubscription repository

**Files:**
- Create: `src/analytis/persistence/repositories/push_subscription.py`

- [ ] **Step 1: Create the repository**

```python
"""Repository for push_subscription table."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.persistence.orm.push import PushSubscriptionORM


@dataclass(frozen=True)
class PushSubscriptionRecord:
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str | None


class PushSubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, sub: PushSubscriptionRecord) -> None:
        """Insert; on endpoint conflict, update last_seen_at + keys."""
        stmt = pg_insert(PushSubscriptionORM).values(
            endpoint=sub.endpoint,
            p256dh=sub.p256dh,
            auth=sub.auth,
            user_agent=sub.user_agent,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["endpoint"],
            set_={
                "p256dh": stmt.excluded.p256dh,
                "auth": stmt.excluded.auth,
                "user_agent": stmt.excluded.user_agent,
                "last_seen_at": stmt.excluded.last_seen_at,
            },
        )
        await self._session.execute(stmt)

    async def delete_by_endpoint(self, endpoint: str) -> None:
        await self._session.execute(
            delete(PushSubscriptionORM).where(PushSubscriptionORM.endpoint == endpoint)
        )

    async def list_all(self) -> list[PushSubscriptionORM]:
        result = await self._session.scalars(select(PushSubscriptionORM))
        return list(result.all())
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from analytis.persistence.repositories.push_subscription import PushSubscriptionRepository; print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add src/analytis/persistence/repositories/push_subscription.py
git commit -m "feat(push): PushSubscriptionRepository with upsert/delete/list"
```

---

## Task 8: PushDispatcher + integration test

**Files:**
- Create: `src/analytis/push/dispatcher.py`
- Create: `tests/integration/push/__init__.py` (empty)
- Create: `tests/integration/push/test_dispatcher.py`

- [ ] **Step 1: Write the failing test (mocking pywebpush)**

Create `tests/integration/push/__init__.py` empty.

Create `tests/integration/push/test_dispatcher.py`:

```python
"""Integration test for PushDispatcher — uses mocked pywebpush."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.persistence.orm.catalog import CompetitionORM, SeasonORM, TeamORM
from analytis.persistence.orm.inference import (
    FeatureSnapshotORM,
    ModelVersionORM,
    PredictionORM,
)
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.orm.push import MatchNotificationORM, PushSubscriptionORM
from analytis.push.dispatcher import PushDispatcher
from analytis.push.vapid import VapidConfig


async def _seed_pre_window_match(session: AsyncSession) -> tuple[MatchORM, ModelVersionORM]:
    """Match kickoff in 10 minutes, with full ensemble prediction set."""
    comp = CompetitionORM(
        id=uuid4(), name="Test", slug=f"t-{uuid4().hex[:8]}",
        competition_type="SELECAO", country="INTL",
    )
    season = SeasonORM(
        id=uuid4(), competition_id=comp.id, label="2026",
        start_date=datetime(2026, 6, 1, tzinfo=UTC).date(),
        end_date=datetime(2026, 7, 30, tzinfo=UTC).date(),
    )
    home = TeamORM(id=uuid4(), name="Home Team", short_name="HOM", team_type="SELECAO", country="X")
    away = TeamORM(id=uuid4(), name="Away Team", short_name="AWA", team_type="SELECAO", country="Y")
    session.add_all([comp, season, home, away])
    await session.flush()

    match = MatchORM(
        id=uuid4(),
        season_id=season.id,
        home_team_id=home.id,
        away_team_id=away.id,
        kickoff_utc=datetime.now(UTC) + timedelta(minutes=10),
        status="scheduled",
        stage="GROUP_STAGE",
        is_home_neutral=False,
    )
    model = ModelVersionORM(
        id=uuid4(), name="ensemble-v1", family="ensemble",
        git_sha="t", hyperparams={}, metrics={}, artifact_path=None,
        trained_at=datetime.now(UTC), is_promoted=False,
    )
    session.add_all([match, model])
    await session.flush()

    snap = FeatureSnapshotORM(
        id=uuid4(), match_id=match.id,
        snapshot_taken_at=datetime.now(UTC), features={},
        created_at=datetime.now(UTC),
    )
    session.add(snap)
    await session.flush()

    for outcome, prob in [("home", 0.55), ("draw", 0.25), ("away", 0.20)]:
        session.add(PredictionORM(
            id=uuid4(), match_id=match.id, model_version_id=model.id,
            market="1x2", outcome=outcome, prob=prob,
            ci_low=prob, ci_high=prob,
            feature_snapshot_id=snap.id, created_at=datetime.now(UTC),
        ))

    await session.commit()
    return match, model


def _vapid() -> VapidConfig:
    return VapidConfig(
        private_key="dGVzdC1wcml2YXRl",  # base64-ish dummy
        public_key="dGVzdC1wdWJsaWM=",
        subject="mailto:test@example.com",
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_dispatch_sends_pre_for_match_in_window(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        match, _ = await _seed_pre_window_match(session)
        session.add(PushSubscriptionORM(
            id=uuid4(),
            endpoint="https://fcm.googleapis.com/fcm/send/x",
            p256dh="p", auth="a", user_agent="ua",
        ))
        await session.commit()

    with patch("analytis.push.dispatcher.webpush") as mock_webpush:
        dispatcher = PushDispatcher(session_factory, _vapid())
        await dispatcher.dispatch()
        assert mock_webpush.called

    async with session_factory() as session:
        notifs = (await session.scalars(
            select(MatchNotificationORM).where(MatchNotificationORM.match_id == match.id)
        )).all()
        assert len(notifs) == 1
        assert notifs[0].kind == "pre"
        assert notifs[0].n_recipients == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_dispatch_skips_already_notified(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        match, _ = await _seed_pre_window_match(session)
        session.add(PushSubscriptionORM(
            id=uuid4(),
            endpoint="https://fcm.googleapis.com/fcm/send/y",
            p256dh="p", auth="a", user_agent="ua",
        ))
        session.add(MatchNotificationORM(
            id=uuid4(), match_id=match.id, kind="pre", n_recipients=1,
        ))
        await session.commit()

    with patch("analytis.push.dispatcher.webpush") as mock_webpush:
        dispatcher = PushDispatcher(session_factory, _vapid())
        await dispatcher.dispatch()
        assert not mock_webpush.called


@pytest.mark.asyncio
@pytest.mark.integration
async def test_dispatch_410_deletes_subscription(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _seed_pre_window_match(session)
        session.add(PushSubscriptionORM(
            id=uuid4(),
            endpoint="https://fcm.googleapis.com/fcm/send/gone",
            p256dh="p", auth="a", user_agent="ua",
        ))
        await session.commit()

    class _FakeException(Exception):
        def __init__(self) -> None:
            class _Resp:
                status_code = 410
            self.response = _Resp()

    with patch("analytis.push.dispatcher.webpush", side_effect=_FakeException()), \
         patch("analytis.push.dispatcher.WebPushException", _FakeException):
        dispatcher = PushDispatcher(session_factory, _vapid())
        await dispatcher.dispatch()

    async with session_factory() as session:
        remaining = (await session.scalars(select(PushSubscriptionORM))).all()
        assert all("gone" not in s.endpoint for s in remaining)
```

- [ ] **Step 2: Run the tests — expect failure (ImportError)**

```bash
uv run pytest tests/integration/push/test_dispatcher.py -v
```

Expected: `ModuleNotFoundError` on `analytis.push.dispatcher`.

- [ ] **Step 3: Implement the dispatcher**

Create `src/analytis/push/dispatcher.py`:

```python
"""PushDispatcher: queries DB, formats payloads, sends via pywebpush."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.inference import ModelVersionORM, PredictionORM
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.orm.push import MatchNotificationORM, PushSubscriptionORM
from analytis.push.bodies import build_post_payload, build_pre_payload
from analytis.push.vapid import VapidConfig

log = logging.getLogger(__name__)

PRE_WINDOW_LO = timedelta(minutes=9)
PRE_WINDOW_HI = timedelta(minutes=11)
POST_LOOKBACK = timedelta(hours=2)
ENSEMBLE_NAME = "ensemble-v1"


@dataclass
class DispatchResult:
    pre_matches: int
    post_matches: int
    subscribers: int
    successes: int
    deleted: int


class PushDispatcher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        vapid: VapidConfig,
    ) -> None:
        self._factory = session_factory
        self._vapid = vapid

    async def dispatch(self) -> DispatchResult:
        result = DispatchResult(
            pre_matches=0, post_matches=0, subscribers=0, successes=0, deleted=0
        )
        async with self._factory() as session:
            pre_matches = await self._find_pre_matches(session)
            post_matches = await self._find_post_matches(session)
            subscriptions = (
                await session.scalars(select(PushSubscriptionORM))
            ).all()
            result.subscribers = len(subscriptions)
            result.pre_matches = len(pre_matches)
            result.post_matches = len(post_matches)

            for match in pre_matches:
                pred = await self._load_ensemble_pred(session, match.id)
                if pred is None:
                    log.warning("no ensemble-v1 prediction for match %s, skipping pre", match.id)
                    continue
                home_name, away_name = await self._team_names(
                    session, match.home_team_id, match.away_team_id
                )
                payload = build_pre_payload(
                    self._match_to_dict(match, home_name, away_name),
                    pred,
                )
                ok, deleted = await self._send_to_all(session, subscriptions, payload)
                result.successes += ok
                result.deleted += deleted
                await self._record_notification(session, match.id, "pre", ok)

            for match in post_matches:
                pred = await self._load_ensemble_pred(session, match.id)
                if pred is None:
                    log.warning("no ensemble-v1 prediction for match %s, skipping post", match.id)
                    continue
                home_name, away_name = await self._team_names(
                    session, match.home_team_id, match.away_team_id
                )
                payload = build_post_payload(
                    self._match_to_dict(match, home_name, away_name),
                    pred,
                )
                ok, deleted = await self._send_to_all(session, subscriptions, payload)
                result.successes += ok
                result.deleted += deleted
                await self._record_notification(session, match.id, "post", ok)

            await session.commit()

        return result

    async def _find_pre_matches(self, session: AsyncSession) -> list[MatchORM]:
        now = datetime.now(UTC)
        stmt = (
            select(MatchORM)
            .where(
                MatchORM.kickoff_utc >= now + PRE_WINDOW_LO,
                MatchORM.kickoff_utc <= now + PRE_WINDOW_HI,
                ~select(MatchNotificationORM.id).where(
                    MatchNotificationORM.match_id == MatchORM.id,
                    MatchNotificationORM.kind == "pre",
                ).exists(),
            )
        )
        return list((await session.scalars(stmt)).all())

    async def _find_post_matches(self, session: AsyncSession) -> list[MatchORM]:
        now = datetime.now(UTC)
        stmt = (
            select(MatchORM)
            .where(
                MatchORM.status == "finished",
                MatchORM.kickoff_utc > now - POST_LOOKBACK,
                ~select(MatchNotificationORM.id).where(
                    MatchNotificationORM.match_id == MatchORM.id,
                    MatchNotificationORM.kind == "post",
                ).exists(),
            )
        )
        return list((await session.scalars(stmt)).all())

    async def _load_ensemble_pred(
        self, session: AsyncSession, match_id: UUID
    ) -> dict[str, float] | None:
        stmt = (
            select(PredictionORM.outcome, PredictionORM.prob)
            .join(ModelVersionORM, ModelVersionORM.id == PredictionORM.model_version_id)
            .where(
                PredictionORM.match_id == match_id,
                ModelVersionORM.name == ENSEMBLE_NAME,
                PredictionORM.market == "1x2",
            )
        )
        rows = (await session.execute(stmt)).all()
        if not rows:
            return None
        return {row.outcome: float(row.prob) for row in rows}

    async def _team_names(
        self, session: AsyncSession, home_id: UUID, away_id: UUID
    ) -> tuple[str, str]:
        result = (
            await session.execute(
                select(TeamORM.id, TeamORM.name).where(TeamORM.id.in_([home_id, away_id]))
            )
        ).all()
        names = {tid: name for tid, name in result}
        return names.get(home_id, "?"), names.get(away_id, "?")

    @staticmethod
    def _match_to_dict(match: MatchORM, home: str, away: str) -> dict:
        return {
            "id": str(match.id),
            "home_team": home,
            "away_team": away,
            "home_goals": match.home_goals,
            "away_goals": match.away_goals,
        }

    async def _send_to_all(
        self,
        session: AsyncSession,
        subscriptions: list[PushSubscriptionORM],
        payload: dict,
    ) -> tuple[int, int]:
        ok = 0
        deleted = 0
        for sub in subscriptions:
            sub_info = {
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            }
            try:
                webpush(
                    subscription_info=sub_info,
                    data=json.dumps(payload),
                    vapid_private_key=self._vapid.private_key,
                    vapid_claims={"sub": self._vapid.subject},
                )
                ok += 1
            except WebPushException as e:
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status == 410:
                    await session.execute(
                        select(PushSubscriptionORM)
                        .where(PushSubscriptionORM.endpoint == sub.endpoint)
                    )
                    await session.delete(sub)
                    deleted += 1
                else:
                    log.warning("webpush failed for %s: %s", sub.endpoint, e)
            except Exception as e:  # noqa: BLE001
                log.warning("unexpected push error for %s: %s", sub.endpoint, e)
        return ok, deleted

    async def _record_notification(
        self, session: AsyncSession, match_id: UUID, kind: str, n_recipients: int
    ) -> None:
        try:
            session.add(MatchNotificationORM(
                match_id=match_id, kind=kind, n_recipients=n_recipients,
            ))
            await session.flush()
        except IntegrityError:
            await session.rollback()
            log.info("match_notification already exists for %s/%s, skipping", match_id, kind)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/push/test_dispatcher.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/analytis/push/dispatcher.py tests/integration/push/__init__.py tests/integration/push/test_dispatcher.py
git commit -m "feat(push): PushDispatcher with pre/post matching + pywebpush + tests"
```

---

## Task 9: FastAPI routes + tests

**Files:**
- Create: `src/analytis/api/routes/push.py`
- Modify: `src/analytis/api/main.py`
- Create: `tests/integration/api/test_push_routes.py`

- [ ] **Step 1: Write failing tests**

Create `tests/integration/api/test_push_routes.py`:

```python
"""Integration tests for /v1/push/* routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.api.main import create_app
from analytis.persistence.orm.push import PushSubscriptionORM

VALID_BODY = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/abc",
    "p256dh": "p256dh-base64",
    "auth": "auth-base64",
    "user_agent": "Mozilla/5.0",
}


@pytest.mark.integration
def test_get_vapid_public_key_returns_200_no_auth(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANALYTIS_VAPID_PUBLIC_KEY", "test-pub-key")
    monkeypatch.setenv("ANALYTIS_VAPID_PRIVATE_KEY", "test-priv-key")
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/push/vapid-public-key")
    assert resp.status_code == 200
    assert resp.json() == {"public_key": "test-pub-key"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_subscribe_creates_row(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.post("/v1/push/subscribe", json=VALID_BODY)
    assert resp.status_code == 201

    async with session_factory() as session:
        rows = (await session.scalars(select(PushSubscriptionORM))).all()
        assert len(rows) == 1
        assert rows[0].endpoint == VALID_BODY["endpoint"]


@pytest.mark.integration
def test_subscribe_rejects_invalid_host(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app = create_app()
    client = TestClient(app)
    body = {**VALID_BODY, "endpoint": "https://evil.example.com/spam"}
    resp = client.post("/v1/push/subscribe", json=body)
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_subscribe_same_endpoint_twice_updates(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app = create_app()
    client = TestClient(app)
    client.post("/v1/push/subscribe", json=VALID_BODY)
    second = {**VALID_BODY, "p256dh": "different-p256dh"}
    resp = client.post("/v1/push/subscribe", json=second)
    assert resp.status_code == 201

    async with session_factory() as session:
        rows = (await session.scalars(select(PushSubscriptionORM))).all()
        assert len(rows) == 1
        assert rows[0].p256dh == "different-p256dh"
```

- [ ] **Step 2: Run tests — expect 404 or import errors**

```bash
uv run pytest tests/integration/api/test_push_routes.py -v
```

Expected: 404 on the endpoint or `ModuleNotFoundError`.

- [ ] **Step 3: Create the route**

Create `src/analytis/api/routes/push.py`:

```python
"""Web push endpoints — vapid public key + subscribe."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from analytis.config import Settings, get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.repositories.push_subscription import (
    PushSubscriptionRecord,
    PushSubscriptionRepository,
)

router = APIRouter(prefix="/push", tags=["push"])

_ALLOWED_HOSTS = {
    "fcm.googleapis.com",
    "updates.push.services.mozilla.com",
    "web.push.apple.com",
}


def _is_allowed_endpoint(endpoint: str) -> bool:
    try:
        host = urlparse(endpoint).hostname or ""
    except ValueError:
        return False
    if host in _ALLOWED_HOSTS:
        return True
    # wns endpoints look like *.notify.windows.com
    if host.endswith(".notify.windows.com"):
        return True
    return False


class VapidPublicKeyResponse(BaseModel):
    public_key: str


class SubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=10)
    p256dh: str = Field(min_length=1)
    auth: str = Field(min_length=1)
    user_agent: str | None = None


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
async def get_vapid_public_key(
    settings: Settings = Depends(get_settings),
) -> VapidPublicKeyResponse:
    if not settings.vapid_public_key:
        raise HTTPException(
            status_code=503, detail="VAPID public key not configured on server"
        )
    return VapidPublicKeyResponse(public_key=settings.vapid_public_key)


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe(
    body: SubscribeRequest,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    if not _is_allowed_endpoint(body.endpoint):
        raise HTTPException(status_code=400, detail="endpoint host not in allowlist")

    engine = create_engine(settings.database_url)
    factory = create_session_factory(engine)
    async with factory() as session:
        repo = PushSubscriptionRepository(session)
        await repo.upsert(
            PushSubscriptionRecord(
                endpoint=body.endpoint,
                p256dh=body.p256dh,
                auth=body.auth,
                user_agent=body.user_agent,
            )
        )
        await session.commit()
    return {"status": "ok"}
```

- [ ] **Step 4: Register router in `main.py`**

Open `src/analytis/api/main.py`. Update the routes import block:

old_string:
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
    push,
    scoreline,
    value_bets,
)
```

And add `app.include_router(push.router, prefix="/v1")` after the `accuracy` line:

old_string:
```python
    app.include_router(accuracy.router, prefix="/v1")
```

new_string:
```python
    app.include_router(accuracy.router, prefix="/v1")
    app.include_router(push.router, prefix="/v1")
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/integration/api/test_push_routes.py -v
```

Expected: 4 PASS.

- [ ] **Step 6: Commit**

```bash
git add src/analytis/api/routes/push.py src/analytis/api/main.py tests/integration/api/test_push_routes.py
git commit -m "feat(api): /v1/push/vapid-public-key + /v1/push/subscribe + tests"
```

---

## Task 10: CLI commands (`analytis push dispatch` + `generate-vapid-keys`)

**Files:**
- Create: `src/analytis/cli/push.py`
- Modify: `src/analytis/cli/app.py`

- [ ] **Step 1: Inspect existing CLI registration pattern**

```bash
cat src/analytis/cli/app.py | head -30
```

Note how other subcommand modules (`backtest`, `score`, `ingest`) are registered.

- [ ] **Step 2: Create the CLI**

Create `src/analytis/cli/push.py`:

```python
"""CLI: analytis push (dispatch + generate-vapid-keys)."""

from __future__ import annotations

import asyncio
import base64

import typer
from py_vapid import Vapid

from analytis.config import get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.push.dispatcher import PushDispatcher
from analytis.push.vapid import load_vapid_config

app = typer.Typer(help="Web Push notifications.")


@app.command("dispatch")
def dispatch() -> None:
    """Run one dispatch cycle: detect pre/post matches and send pushes."""
    settings = get_settings()
    private_key = (
        settings.vapid_private_key.get_secret_value()
        if settings.vapid_private_key is not None
        else None
    )
    vapid = load_vapid_config(
        private_key=private_key,
        public_key=settings.vapid_public_key,
        subject=settings.vapid_subject,
    )
    engine = create_engine(settings.database_url)
    factory = create_session_factory(engine)
    dispatcher = PushDispatcher(factory, vapid)
    result = asyncio.run(dispatcher.dispatch())
    typer.echo(
        f"pre={result.pre_matches} post={result.post_matches} "
        f"subs={result.subscribers} sent={result.successes} deleted={result.deleted}"
    )


@app.command("generate-vapid-keys")
def generate_vapid_keys() -> None:
    """Generate a fresh VAPID keypair and print as base64 url-safe strings."""
    vapid = Vapid()
    vapid.generate_keys()
    priv_der = vapid.private_key.private_bytes_raw()
    pub_uncompressed = vapid.public_key.public_bytes_raw()
    priv_b64 = base64.urlsafe_b64encode(priv_der).rstrip(b"=").decode()
    pub_b64 = base64.urlsafe_b64encode(pub_uncompressed).rstrip(b"=").decode()
    typer.echo(f"ANALYTIS_VAPID_PRIVATE_KEY={priv_b64}")
    typer.echo(f"ANALYTIS_VAPID_PUBLIC_KEY={pub_b64}")
    typer.echo("# Copy these to deploy/.env.prod (do NOT commit)")
```

- [ ] **Step 3: Register `push` subcommand in `app.py`**

Open `src/analytis/cli/app.py`. Add the import alongside existing CLI subcommand imports (e.g. next to where `from analytis.cli import score` or similar lives):

```python
from analytis.cli import push
```

And register the subcommand by adding (next to the existing `app.add_typer(...)` calls):

```python
app.add_typer(push.app, name="push")
```

If the structure differs (e.g. the file uses a different way of bundling sub-typers), inspect the existing pattern and adapt.

- [ ] **Step 4: Verify CLI registration**

```bash
uv run analytis push --help
```

Expected: shows `dispatch` and `generate-vapid-keys` subcommands.

- [ ] **Step 5: Smoke-test key generation**

```bash
uv run analytis push generate-vapid-keys
```

Expected: prints two lines `ANALYTIS_VAPID_PRIVATE_KEY=...` and `ANALYTIS_VAPID_PUBLIC_KEY=...`, plus a comment line.

- [ ] **Step 6: Commit**

```bash
git add src/analytis/cli/push.py src/analytis/cli/app.py
git commit -m "feat(cli): analytis push dispatch + generate-vapid-keys"
```

---

## Task 11: Frontend — service worker

**Files:**
- Create: `frontend/public/sw.js`

- [ ] **Step 1: Create the service worker**

```javascript
// frontend/public/sw.js — handles incoming push events and notification clicks.
self.addEventListener("push", (event) => {
  if (!event.data) return;
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      data: { url: data.url ?? "/" },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url ?? "/";
  event.waitUntil(
    (async () => {
      const allClients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      for (const client of allClients) {
        if (client.url.includes(targetUrl)) {
          client.focus();
          return;
        }
      }
      await self.clients.openWindow(targetUrl);
    })(),
  );
});
```

- [ ] **Step 2: Verify the build copies it**

```bash
cd "C:/Projetos/Pessoal/analytis/frontend"
pnpm build
ls dist/ | grep sw
```

Expected: `sw.js` shows in `dist/`.

- [ ] **Step 3: Commit**

```bash
cd "C:/Projetos/Pessoal/analytis"
git add frontend/public/sw.js
git commit -m "feat(pwa): service worker for push events"
```

---

## Task 12: Frontend — push.ts library

**Files:**
- Create: `frontend/src/lib/push.ts`

- [ ] **Step 1: Create the helper**

```typescript
// frontend/src/lib/push.ts — register SW, request permission, POST subscription.

const SUBSCRIBED_FLAG = "analytis_push_subscribed";
const ASKED_FLAG = "analytis_push_asked";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const output = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i += 1) output[i] = rawData.charCodeAt(i);
  return output;
}

export function isPushSupported(): boolean {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

export function isInstalledPwa(): boolean {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (window.navigator as { standalone?: boolean }).standalone === true
  );
}

export function hasBeenAsked(): boolean {
  return localStorage.getItem(ASKED_FLAG) === "true";
}

export function isSubscribed(): boolean {
  return localStorage.getItem(SUBSCRIBED_FLAG) === "true";
}

export function markAsked(): void {
  localStorage.setItem(ASKED_FLAG, "true");
}

export async function enablePush(): Promise<void> {
  if (!isPushSupported()) throw new Error("push not supported");

  const keyResp = await fetch("/v1/push/vapid-public-key");
  if (!keyResp.ok) throw new Error(`vapid-public-key failed: ${keyResp.status}`);
  const { public_key } = (await keyResp.json()) as { public_key: string };

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    markAsked();
    throw new Error("permission denied");
  }

  const registration = await navigator.serviceWorker.register("/sw.js");
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(public_key),
  });

  const json = subscription.toJSON();
  const subResp = await fetch("/v1/push/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      endpoint: json.endpoint,
      p256dh: json.keys?.p256dh,
      auth: json.keys?.auth,
      user_agent: navigator.userAgent,
    }),
  });
  if (!subResp.ok) throw new Error(`subscribe failed: ${subResp.status}`);

  localStorage.setItem(SUBSCRIBED_FLAG, "true");
  markAsked();
}
```

- [ ] **Step 2: Typecheck**

```bash
cd "C:/Projetos/Pessoal/analytis/frontend"
pnpm typecheck
```

Expected: clean exit.

- [ ] **Step 3: Commit**

```bash
cd "C:/Projetos/Pessoal/analytis"
git add frontend/src/lib/push.ts
git commit -m "feat(frontend): push.ts — enable/check Web Push subscription"
```

---

## Task 13: Frontend — PushPrompt component

**Files:**
- Create: `frontend/src/components/PushPrompt.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create the component**

```typescript
// frontend/src/components/PushPrompt.tsx
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  enablePush,
  hasBeenAsked,
  isInstalledPwa,
  isPushSupported,
  isSubscribed,
  markAsked,
} from "@/lib/push";

export function PushPrompt() {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isPushSupported()) return;
    if (!isInstalledPwa()) return;
    if (hasBeenAsked()) return;
    if (isSubscribed()) return;
    if (Notification.permission !== "default") return;
    setOpen(true);
  }, []);

  const handleAccept = async () => {
    setBusy(true);
    try {
      await enablePush();
    } catch {
      // permission denied or network error — markAsked already invoked inside push.ts when relevant
    } finally {
      setBusy(false);
      setOpen(false);
    }
  };

  const handleLater = () => {
    markAsked();
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleLater()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Receber notificações dos jogos?</DialogTitle>
          <DialogDescription>
            Você vai receber um alerta 10 minutos antes de cada partida da Copa
            (com a previsão do modelo) e logo após o apito final (com o resultado e
            se a previsão acertou).
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="ghost" onClick={handleLater} disabled={busy}>
            Mais tarde
          </Button>
          <Button variant="gradient" onClick={handleAccept} disabled={busy}>
            {busy ? "Configurando..." : "Sim, ativar"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: Mount in `App.tsx`**

Open `frontend/src/App.tsx`. Add the import next to the existing `ApiKeyDialog` import:

old_string:
```typescript
import { ApiKeyDialog } from "@/components/ApiKeyDialog";
```

new_string:
```typescript
import { ApiKeyDialog } from "@/components/ApiKeyDialog";
import { PushPrompt } from "@/components/PushPrompt";
```

Mount it next to `<ApiKeyDialog />`:

old_string:
```typescript
        <ApiKeyDialog />
```

new_string:
```typescript
        <ApiKeyDialog />
        <PushPrompt />
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
git add frontend/src/components/PushPrompt.tsx frontend/src/App.tsx
git commit -m "feat(frontend): PushPrompt modal on first PWA open"
```

---

## Task 14: Cron script + finish.sh

**Files:**
- Create: `deploy/cron/push-dispatcher.sh`
- Modify: `deploy/finish.sh`
- Modify: `deploy/.env.prod.example`

- [ ] **Step 1: Create the cron wrapper**

Write `deploy/cron/push-dispatcher.sh`:

```bash
#!/usr/bin/env bash
# Per-minute cron: dispatches pre/post-match push notifications via the analytis CLI.
set -euo pipefail

REPO_ROOT="/opt/analytis"
LOG_DIR="$REPO_ROOT/logs"
LOG="$LOG_DIR/push-dispatcher.log"
LOCK="/tmp/analytis-push-dispatcher.lock"

mkdir -p "$LOG_DIR"

exec 9>"$LOCK"
flock -n 9 || exit 0

{
  echo "=== $(date -u +%FT%TZ) push-dispatch start ==="
  docker compose -f "$REPO_ROOT/deploy/docker-compose.prod.yml" \
    --env-file "$REPO_ROOT/deploy/.env.prod" \
    exec -T app analytis push dispatch
  echo "=== $(date -u +%FT%TZ) push-dispatch done ==="
} >> "$LOG" 2>&1
```

- [ ] **Step 2: Add cron entry in `finish.sh`**

Open `deploy/finish.sh`. Find the existing cron block (where `analytis-rescore` is installed) and add another:

old_string:
```bash
sudo tee /etc/cron.d/analytis-rescore >/dev/null <<EOF
0 7 * * * root /opt/analytis/deploy/cron/daily-rescore.sh
EOF
```

new_string:
```bash
sudo tee /etc/cron.d/analytis-rescore >/dev/null <<EOF
0 7 * * * root /opt/analytis/deploy/cron/daily-rescore.sh
EOF

sudo chmod +x /opt/analytis/deploy/cron/push-dispatcher.sh
sudo tee /etc/cron.d/analytis-push >/dev/null <<EOF
* * * * * root /opt/analytis/deploy/cron/push-dispatcher.sh
EOF
```

- [ ] **Step 3: Add VAPID placeholders to `.env.prod.example`**

Open `deploy/.env.prod.example`. Append:

```bash
# Web Push VAPID keys (generate via: uv run analytis push generate-vapid-keys)
ANALYTIS_VAPID_PRIVATE_KEY=<run-the-cli-locally-and-paste-here>
ANALYTIS_VAPID_PUBLIC_KEY=<run-the-cli-locally-and-paste-here>
ANALYTIS_VAPID_SUBJECT=mailto:techeasy376@gmail.com
```

- [ ] **Step 4: Commit**

```bash
git add deploy/cron/push-dispatcher.sh deploy/finish.sh deploy/.env.prod.example
git commit -m "feat(deploy): per-minute push-dispatcher cron + VAPID env vars"
```

---

## Task 15: Generate VAPID keys and update .env.prod

**Files:**
- Modify: `deploy/.env.prod` (gitignored — NEVER commit)

- [ ] **Step 1: Generate the keys locally**

```bash
cd "C:/Projetos/Pessoal/analytis"
uv run analytis push generate-vapid-keys
```

Expected: prints `ANALYTIS_VAPID_PRIVATE_KEY=<long-base64>` and `ANALYTIS_VAPID_PUBLIC_KEY=<short-base64>`. Save both values temporarily.

- [ ] **Step 2: Update `.env.prod` (gitignored)**

Open `deploy/.env.prod`. Append the three lines:

```bash
ANALYTIS_VAPID_PRIVATE_KEY=<paste-private-from-step-1>
ANALYTIS_VAPID_PUBLIC_KEY=<paste-public-from-step-1>
ANALYTIS_VAPID_SUBJECT=mailto:techeasy376@gmail.com
```

- [ ] **Step 3: DO NOT commit**

`deploy/.env.prod` is in `.gitignore`. If a commit is staged that includes it by accident, abort.

```bash
git status --short | grep "\.env\.prod"
```

Expected: shows untracked, never modified-as-staged.

---

## Task 16: Deploy + production smoke test

**Files:** none (deploy only)

- [ ] **Step 1: Run deploy**

```bash
cd "C:/Projetos/Pessoal/analytis"
bash deploy/deploy.sh
```

Expected: `[deploy] Done.` after build + upload + load + migrate + cron install.

- [ ] **Step 2: Confirm migration 0005 applied in prod**

```bash
ssh ubuntu@163.176.194.231 'sudo docker compose -f /opt/analytis/deploy/docker-compose.prod.yml --env-file /opt/analytis/deploy/.env.prod exec -T postgres psql -U analytis -d analytis -c "\d push_subscription"' | tail -10
```

Expected: table description with the 6 columns.

- [ ] **Step 3: Smoke test the endpoint**

```bash
curl -fsS --resolve analytis.zyntra.company:443:163.176.194.231 \
  https://analytis.zyntra.company/v1/push/vapid-public-key
```

Expected: JSON `{"public_key": "..."}`.

- [ ] **Step 4: Verify cron is installed**

```bash
ssh ubuntu@163.176.194.231 'cat /etc/cron.d/analytis-push'
```

Expected: `* * * * * root /opt/analytis/deploy/cron/push-dispatcher.sh`.

- [ ] **Step 5: Trigger cron manually + inspect log**

```bash
ssh ubuntu@163.176.194.231 'sudo /opt/analytis/deploy/cron/push-dispatcher.sh; tail -5 /opt/analytis/logs/push-dispatcher.log'
```

Expected: a line like `pre=0 post=0 subs=0 sent=0 deleted=0` (no matches in window, no subscribers yet) and no Python tracebacks.

---

## Task 17: iPhone install validation (manual, by project owner)

**Files:** none (user task)

- [ ] **Step 1: Update PWA on iPhone**

Open Safari, navigate to `https://analytis.zyntra.company`, hard refresh. Then open the installed PWA from home screen.

- [ ] **Step 2: Accept the prompt**

Modal "Receber notificações dos jogos?" appears. Tap **Sim, ativar**.

iOS native popup asks for notification permission. Tap **Permitir**.

- [ ] **Step 3: Confirm subscription on VM**

```bash
ssh ubuntu@163.176.194.231 'sudo docker compose -f /opt/analytis/deploy/docker-compose.prod.yml --env-file /opt/analytis/deploy/.env.prod exec -T postgres psql -U analytis -d analytis -c "SELECT endpoint, user_agent FROM push_subscription"'
```

Expected: one row with your iPhone's endpoint + iOS Safari UA string.

- [ ] **Step 4: Trigger a test notification by faking a kickoff**

Pick a scheduled match in 1+ hour and temporarily move its kickoff to ~10 min from now:

```bash
ssh ubuntu@163.176.194.231 'sudo docker compose -f /opt/analytis/deploy/docker-compose.prod.yml --env-file /opt/analytis/deploy/.env.prod exec -T postgres psql -U analytis -d analytis -c "UPDATE match SET kickoff_utc = NOW() + INTERVAL '\''10 minutes'\'' WHERE id = (SELECT id FROM match WHERE status='\''scheduled'\'' ORDER BY kickoff_utc LIMIT 1) RETURNING id, home_team_id"'
```

- [ ] **Step 5: Wait up to 1 minute, then confirm notification arrives**

Notification arrives on iPhone lockscreen. Tap it. PWA opens on `/matches/<uuid>`.

- [ ] **Step 6: Confirm idempotency**

Trigger the cron manually a second time:

```bash
ssh ubuntu@163.176.194.231 'sudo /opt/analytis/deploy/cron/push-dispatcher.sh; tail -5 /opt/analytis/logs/push-dispatcher.log'
```

Expected: log shows `pre=0` (already notified), no second notification arrives on iPhone.

- [ ] **Step 7: Restore the test match kickoff**

If you cherry-picked a real Copa fixture in step 4, restore its kickoff:

```bash
ssh ubuntu@163.176.194.231 'sudo docker compose -f /opt/analytis/deploy/docker-compose.prod.yml --env-file /opt/analytis/deploy/.env.prod exec -T app analytis ingest fixtures --competition 2000 --season 2026'
```

Re-ingest from Football-Data overwrites the kickoff back to the real value.

---

## Plan-vs-spec self-review

**Spec coverage:**

- ✅ Service worker → Task 11
- ✅ Permission prompt auto on PWA open → Tasks 12, 13
- ✅ Backend tables → Tasks 3, 4
- ✅ Routes `vapid-public-key` + `subscribe` with host whitelist → Task 9
- ✅ CLI `dispatch` + `generate-vapid-keys` → Task 10
- ✅ pywebpush + py-vapid deps → Task 1
- ✅ VAPID config from env → Tasks 2, 5
- ✅ Body builders pre + post → Task 6
- ✅ Dispatcher with 410 cleanup + idempotency → Task 8
- ✅ Cron with flock → Task 14
- ✅ One-shot VAPID key generation → Task 15
- ✅ Deploy + manual e2e → Tasks 16, 17

**Placeholder scan:** No "TBD", "TODO", or vague "handle errors appropriately" — every step has explicit code or commands.

**Type consistency:**
- `PushSubscriptionRecord` defined in Task 7, consumed in Task 9 — matches
- `VapidConfig` defined in Task 5, consumed in Task 8 and Task 10 — matches
- `DispatchResult` defined inside dispatcher in Task 8, consumed in CLI Task 10 via attribute access — matches
- Route response shapes (`VapidPublicKeyResponse`, `SubscribeRequest`) defined and used in Task 9 — internally consistent
- Frontend `enablePush()` calls the routes defined in Task 9 with matching body fields — matches
