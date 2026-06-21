"""Integration tests for PushDispatcher — uses mocked pywebpush."""

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


async def _seed_pre_window_match(
    session: AsyncSession,
) -> tuple[MatchORM, ModelVersionORM]:
    """Match kickoff in 10 minutes, with full ensemble prediction set."""
    comp = CompetitionORM(
        id=uuid4(),
        name="Test",
        slug=f"t-{uuid4().hex[:8]}",
        competition_type="SELECAO",
        country="INTL",
    )
    season = SeasonORM(
        id=uuid4(),
        competition_id=comp.id,
        label="2026",
        start_date=datetime(2026, 6, 1, tzinfo=UTC).date(),
        end_date=datetime(2026, 7, 30, tzinfo=UTC).date(),
    )
    home = TeamORM(
        id=uuid4(),
        name=f"Home-{uuid4().hex[:6]}",
        short_name="HOM",
        team_type="SELECAO",
        country="X",
    )
    away = TeamORM(
        id=uuid4(),
        name=f"Away-{uuid4().hex[:6]}",
        short_name="AWA",
        team_type="SELECAO",
        country="Y",
    )
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
        id=uuid4(),
        name="ensemble-v1",
        family="ensemble",
        git_sha="t",
        hyperparams={},
        metrics={},
        artifact_path=None,
        trained_at=datetime.now(UTC),
        is_promoted=False,
    )
    session.add_all([match, model])
    await session.flush()

    snap = FeatureSnapshotORM(
        id=uuid4(),
        match_id=match.id,
        snapshot_taken_at=datetime.now(UTC),
        features={},
        created_at=datetime.now(UTC),
    )
    session.add(snap)
    await session.flush()

    for outcome, prob in [("home", 0.55), ("draw", 0.25), ("away", 0.20)]:
        session.add(
            PredictionORM(
                id=uuid4(),
                match_id=match.id,
                model_version_id=model.id,
                market="1x2",
                outcome=outcome,
                prob=prob,
                ci_low=prob,
                ci_high=prob,
                feature_snapshot_id=snap.id,
                created_at=datetime.now(UTC),
            )
        )

    await session.commit()
    return match, model


def _vapid() -> VapidConfig:
    return VapidConfig(
        private_key="dGVzdC1wcml2YXRl",
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
        session.add(
            PushSubscriptionORM(
                id=uuid4(),
                endpoint="https://fcm.googleapis.com/fcm/send/x",
                p256dh="p",
                auth="a",
                user_agent="ua",
                created_at=datetime.now(UTC),
                last_seen_at=datetime.now(UTC),
            )
        )
        await session.commit()

    with patch("analytis.push.dispatcher.webpush") as mock_webpush:
        dispatcher = PushDispatcher(session_factory, _vapid())
        await dispatcher.dispatch()
        assert mock_webpush.called

    async with session_factory() as session:
        notifs = (
            await session.scalars(
                select(MatchNotificationORM).where(MatchNotificationORM.match_id == match.id)
            )
        ).all()
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
        session.add(
            PushSubscriptionORM(
                id=uuid4(),
                endpoint="https://fcm.googleapis.com/fcm/send/y",
                p256dh="p",
                auth="a",
                user_agent="ua",
                created_at=datetime.now(UTC),
                last_seen_at=datetime.now(UTC),
            )
        )
        session.add(
            MatchNotificationORM(
                id=uuid4(),
                match_id=match.id,
                kind="pre",
                n_recipients=1,
                sent_at=datetime.now(UTC),
            )
        )
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
        session.add(
            PushSubscriptionORM(
                id=uuid4(),
                endpoint="https://fcm.googleapis.com/fcm/send/gone",
                p256dh="p",
                auth="a",
                user_agent="ua",
                created_at=datetime.now(UTC),
                last_seen_at=datetime.now(UTC),
            )
        )
        await session.commit()

    class _FakeException(Exception):
        def __init__(self) -> None:
            class _Resp:
                status_code = 410

            self.response = _Resp()

    with (
        patch("analytis.push.dispatcher.webpush", side_effect=_FakeException()),
        patch("analytis.push.dispatcher.WebPushException", _FakeException),
    ):
        dispatcher = PushDispatcher(session_factory, _vapid())
        await dispatcher.dispatch()

    async with session_factory() as session:
        remaining = (await session.scalars(select(PushSubscriptionORM))).all()
        assert all("gone" not in s.endpoint for s in remaining)
