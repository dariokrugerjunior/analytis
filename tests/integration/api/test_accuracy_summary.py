"""Integration tests for GET /v1/accuracy/summary."""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.api.main import create_app
from analytis.persistence.orm.catalog import CompetitionORM, SeasonORM, TeamORM
from analytis.persistence.orm.inference import (
    FeatureSnapshotORM,
    ModelVersionORM,
    PredictionORM,
)
from analytis.persistence.orm.matches import MatchORM


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


async def _seed_full_match_with_prediction(
    session: AsyncSession,
    *,
    model_id: UUID,
    kickoff: datetime,
    stage: str,
    score: tuple[int, int],
    probs_1x2: dict[str, float],
    prob_over: float,
    prob_btts_yes: float,
) -> MatchORM:
    """Helper: seed 1 finished match + full prediction set for 1 model."""
    _, season = await _seed_competition(session)
    home_name = f"H-{kickoff.day}-{kickoff.hour}"
    away_name = f"A-{kickoff.day}-{kickoff.hour}"
    teams = await _seed_teams(session, [home_name, away_name])
    home_goals, away_goals = score
    match = await _seed_match(
        session,
        season_id=season.id,
        home=teams[home_name],
        away=teams[away_name],
        kickoff=kickoff,
        stage=stage,
        home_goals=home_goals,
        away_goals=away_goals,
    )
    snap = await _seed_snapshot(session, match.id)
    for outcome, p in probs_1x2.items():
        await _seed_prediction(
            session,
            match_id=match.id,
            model_id=model_id,
            snapshot_id=snap.id,
            market="1x2",
            outcome=outcome,
            prob=p,
        )
    await _seed_prediction(
        session,
        match_id=match.id,
        model_id=model_id,
        snapshot_id=snap.id,
        market="over_under_2_5",
        outcome="over",
        prob=prob_over,
    )
    await _seed_prediction(
        session,
        match_id=match.id,
        model_id=model_id,
        snapshot_id=snap.id,
        market="over_under_2_5",
        outcome="under",
        prob=1.0 - prob_over,
    )
    await _seed_prediction(
        session,
        match_id=match.id,
        model_id=model_id,
        snapshot_id=snap.id,
        market="btts",
        outcome="yes",
        prob=prob_btts_yes,
    )
    await _seed_prediction(
        session,
        match_id=match.id,
        model_id=model_id,
        snapshot_id=snap.id,
        market="btts",
        outcome="no",
        prob=1.0 - prob_btts_yes,
    )
    return match


# ============================================================
# Coverage tests
# ============================================================


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_returns_404_when_model_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A ?model=ghost query for a non-existent model returns 404."""
    async with session_factory() as session:
        _, season = await _seed_competition(session)
        teams = await _seed_teams(session, ["Brazil", "Argentina"])
        match = await _seed_match(
            session,
            season_id=season.id,
            home=teams["Brazil"],
            away=teams["Argentina"],
            kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
            stage="GROUP_STAGE",
            home_goals=2,
            away_goals=1,
        )
        real = await _seed_model(session, name="real-model", family="dixon-coles")
        snap = await _seed_snapshot(session, match.id)
        await _seed_prediction(
            session,
            match_id=match.id,
            model_id=real.id,
            snapshot_id=snap.id,
            market="1x2",
            outcome="home",
            prob=0.6,
        )
        await session.commit()

    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/accuracy/summary?model=ghost")
    assert resp.status_code == 404
    assert "ghost" in resp.json()["detail"]
    del client, app
    gc.collect()


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_returns_only_finished_matches(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Only finished matches are counted; scheduled matches are excluded."""
    async with session_factory() as session:
        _, season = await _seed_competition(session)
        teams = await _seed_teams(session, ["Brazil", "Argentina"])
        finished_match = await _seed_match(
            session,
            season_id=season.id,
            home=teams["Brazil"],
            away=teams["Argentina"],
            kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
            stage="GROUP_STAGE",
            home_goals=2,
            away_goals=1,
        )
        scheduled_match = await _seed_match(
            session,
            season_id=season.id,
            home=teams["Argentina"],
            away=teams["Brazil"],
            kickoff=datetime(2026, 6, 20, 18, 0, tzinfo=UTC),
            stage="GROUP_STAGE",
            status="scheduled",
        )
        model = await _seed_model(session, name="m1", family="dixon-coles")
        snap_f = await _seed_snapshot(session, finished_match.id)
        snap_s = await _seed_snapshot(session, scheduled_match.id)
        for outcome, prob in [("home", 0.6), ("draw", 0.25), ("away", 0.15)]:
            await _seed_prediction(
                session,
                match_id=finished_match.id,
                model_id=model.id,
                snapshot_id=snap_f.id,
                market="1x2",
                outcome=outcome,
                prob=prob,
            )
            await _seed_prediction(
                session,
                match_id=scheduled_match.id,
                model_id=model.id,
                snapshot_id=snap_s.id,
                market="1x2",
                outcome=outcome,
                prob=prob,
            )
        await session.commit()

    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/accuracy/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["kpis"]["n_matches_evaluated"] == 1
    assert body["kpis"]["markets"]["1x2"]["n"] == 1
    del client, app
    gc.collect()


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_1x2_argmax_correctness(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Home wins with highest home probability → 1x2 hit counted."""
    async with session_factory() as session:
        model = await _seed_model(session, name="m", family="dc")
        await _seed_full_match_with_prediction(
            session,
            model_id=model.id,
            kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
            stage="GROUP_STAGE",
            score=(2, 1),
            probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
            prob_over=0.7,
            prob_btts_yes=0.7,
        )
        await session.commit()

    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/accuracy/summary?model=m")
    body = resp.json()
    assert body["kpis"]["markets"]["1x2"]["hits"] == 1
    assert body["kpis"]["markets"]["1x2"]["n"] == 1
    del client, app
    gc.collect()


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_ou_threshold_at_0_5(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """1-1 is under 2.5; prob_over=0.51 predicts 'over' → miss."""
    async with session_factory() as session:
        model = await _seed_model(session, name="m", family="dc")
        await _seed_full_match_with_prediction(
            session,
            model_id=model.id,
            kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
            stage="GROUP_STAGE",
            score=(1, 1),
            probs_1x2={"home": 0.4, "draw": 0.4, "away": 0.2},
            prob_over=0.51,
            prob_btts_yes=0.7,
        )
        await session.commit()

    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/accuracy/summary?model=m")
    body = resp.json()
    assert body["kpis"]["markets"]["ou"]["hits"] == 0
    del client, app
    gc.collect()


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_btts_threshold_at_0_5(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """2-1: BTTS=yes. prob_btts_yes=0.49 → predict 'no' → miss."""
    async with session_factory() as session:
        model = await _seed_model(session, name="m", family="dc")
        await _seed_full_match_with_prediction(
            session,
            model_id=model.id,
            kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
            stage="GROUP_STAGE",
            score=(2, 1),
            probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
            prob_over=0.7,
            prob_btts_yes=0.49,
        )
        await session.commit()

    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/accuracy/summary?model=m")
    body = resp.json()
    assert body["kpis"]["markets"]["btts"]["hits"] == 0
    del client, app
    gc.collect()


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_brier_avg_calculation(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """prob_over=1.0 (brier=0) and prob_over=0.0 (brier=1) → avg=0.5."""
    async with session_factory() as session:
        model = await _seed_model(session, name="m", family="dc")
        await _seed_full_match_with_prediction(
            session,
            model_id=model.id,
            kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
            stage="GROUP_STAGE",
            score=(2, 1),  # over
            probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
            prob_over=1.0,
            prob_btts_yes=0.5,
        )
        await _seed_full_match_with_prediction(
            session,
            model_id=model.id,
            kickoff=datetime(2026, 6, 15, 18, 0, tzinfo=UTC),
            stage="GROUP_STAGE",
            score=(2, 1),  # over
            probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
            prob_over=0.0,
            prob_btts_yes=0.5,
        )
        await session.commit()

    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/accuracy/summary?model=m")
    body = resp.json()
    assert body["kpis"]["markets"]["ou"]["brier_avg"] == pytest.approx(0.5, abs=1e-6)
    del client, app
    gc.collect()


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_timeseries_n_monotonic(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """`n` in the timeseries must be non-decreasing across phases."""
    async with session_factory() as session:
        model = await _seed_model(session, name="m", family="dc")
        for day, stage in enumerate(["GROUP_STAGE", "LAST_16", "QUARTER_FINALS"], start=14):
            await _seed_full_match_with_prediction(
                session,
                model_id=model.id,
                kickoff=datetime(2026, 6, day, 18, 0, tzinfo=UTC),
                stage=stage,
                score=(2, 1),
                probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
                prob_over=0.7,
                prob_btts_yes=0.7,
            )
        await session.commit()

    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/accuracy/summary?model=m")
    body = resp.json()
    ns = [point["n"] for point in body["timeseries"]]
    assert ns == sorted(ns), f"n should be non-decreasing, got {ns}"
    del client, app
    gc.collect()


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_phase_normalization_in_response(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """LAST_16 stage is normalized to 'round_of_16' in the response."""
    async with session_factory() as session:
        model = await _seed_model(session, name="m", family="dc")
        await _seed_full_match_with_prediction(
            session,
            model_id=model.id,
            kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
            stage="LAST_16",
            score=(2, 1),
            probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
            prob_over=0.7,
            prob_btts_yes=0.7,
        )
        await session.commit()

    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/accuracy/summary?model=m")
    body = resp.json()
    assert body["matches"][0]["phase"] == "round_of_16"
    del client, app
    gc.collect()


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_empty_db_returns_404(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """No models seeded → 404 with appropriate message."""
    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/accuracy/summary")
    assert resp.status_code == 404
    del client, app
    gc.collect()


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
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

    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/accuracy/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["model"]["name"] == "a-model"  # alphabetical default
    names = [m["name"] for m in body["available_models"]]
    assert names == sorted(names)  # alphabetical order
    del client, app
    gc.collect()
