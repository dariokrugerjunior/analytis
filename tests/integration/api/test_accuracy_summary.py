"""Integration tests for GET /v1/accuracy/summary."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.api.main import create_app
from analytis.config import get_settings
from analytis.persistence.orm.catalog import CompetitionORM, SeasonORM, TeamORM
from analytis.persistence.orm.inference import (
    FeatureSnapshotORM,
    ModelVersionORM,
    PredictionORM,
)
from analytis.persistence.orm.matches import MatchORM


def _api_key_header() -> dict[str, str]:
    return {"X-API-Key": get_settings().api_key.get_secret_value()}


async def _seed_competition(session: AsyncSession) -> tuple[CompetitionORM, SeasonORM]:
    comp = CompetitionORM(
        id=uuid4(),
        name="Copa Test",
        slug=f"copa-test-{uuid4().hex[:8]}",
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
    session.add_all([comp, season])
    await session.flush()
    return comp, season


async def _seed_teams(session: AsyncSession, names: list[str]) -> dict[str, TeamORM]:
    teams = {
        n: TeamORM(
            id=uuid4(),
            name=n,
            short_name=n[:5].upper(),
            team_type="SELECAO",
            country="INT",
        )
        for n in names
    }
    session.add_all(list(teams.values()))
    await session.flush()
    return teams


async def _seed_match(
    session: AsyncSession,
    *,
    season_id: UUID,
    home: TeamORM,
    away: TeamORM,
    kickoff: datetime,
    stage: str = "GROUP_STAGE",
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
        status=status,
        stage=stage,
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


async def _seed_snapshot(session: AsyncSession, match_id: UUID) -> FeatureSnapshotORM:
    snap = FeatureSnapshotORM(
        id=uuid4(),
        match_id=match_id,
        snapshot_taken_at=datetime.now(UTC),
        features={},
        created_at=datetime.now(UTC),
    )
    session.add(snap)
    await session.flush()
    return snap


async def _seed_prediction(
    session: AsyncSession,
    *,
    match_id: UUID,
    model_id: UUID,
    snapshot_id: UUID,
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
            feature_snapshot_id=snapshot_id,
            created_at=datetime.now(UTC),
        )
    )


@pytest.mark.integration
async def test_default_model_picks_first_alphabetical_with_predictions(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """No ?model param → first alphabetical model with predictions."""
    async with session_factory() as session:
        _comp, season = await _seed_competition(session)
        teams = await _seed_teams(session, ["Brazil", "Argentina"])
        match = await _seed_match(
            session,
            season_id=season.id,
            home=teams["Brazil"],
            away=teams["Argentina"],
            kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
            home_goals=2,
            away_goals=1,
        )
        model_z = await _seed_model(session, name="z-model", family="dixon-coles")
        model_a = await _seed_model(session, name="a-model", family="xgboost")
        snap_z = await _seed_snapshot(session, match.id)
        snap_a = await _seed_snapshot(session, match.id)
        for outcome, prob in [("home", 0.6), ("draw", 0.25), ("away", 0.15)]:
            await _seed_prediction(
                session,
                match_id=match.id,
                model_id=model_z.id,
                snapshot_id=snap_z.id,
                market="1x2",
                outcome=outcome,
                prob=prob,
            )
            await _seed_prediction(
                session,
                match_id=match.id,
                model_id=model_a.id,
                snapshot_id=snap_a.id,
                market="1x2",
                outcome=outcome,
                prob=prob,
            )
        await _seed_prediction(
            session,
            match_id=match.id,
            model_id=model_z.id,
            snapshot_id=snap_z.id,
            market="over_under_2_5",
            outcome="over",
            prob=0.7,
        )
        await _seed_prediction(
            session,
            match_id=match.id,
            model_id=model_a.id,
            snapshot_id=snap_a.id,
            market="over_under_2_5",
            outcome="over",
            prob=0.7,
        )
        await _seed_prediction(
            session,
            match_id=match.id,
            model_id=model_z.id,
            snapshot_id=snap_z.id,
            market="btts",
            outcome="yes",
            prob=0.65,
        )
        await _seed_prediction(
            session,
            match_id=match.id,
            model_id=model_a.id,
            snapshot_id=snap_a.id,
            market="btts",
            outcome="yes",
            prob=0.65,
        )
        await session.commit()

    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/accuracy/summary", headers=_api_key_header())
    assert resp.status_code == 200
    body = resp.json()
    assert body["model"]["name"] == "a-model"  # alphabetical default
    names = [m["name"] for m in body["available_models"]]
    assert names == sorted(names)  # alphabetical order
