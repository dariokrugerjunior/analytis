"""Integration tests for GET /v1/dashboard/scores."""

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
    score: tuple[int, int],
    probs_1x2: dict[str, float],
    prob_over: float,
    prob_btts_yes: float,
    stage: str = "GROUP_STAGE",
) -> MatchORM:
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


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_scores_shape_and_grading(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A finished match with an ensemble prediction is graded 0/50/100 and the
    aggregate counts sum to the number of games."""
    async with session_factory() as session:
        model = await _seed_model(session, name="ensemble-v1", family="ensemble")
        await _seed_full_match_with_prediction(
            session,
            model_id=model.id,
            kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
            score=(2, 1),
            probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
            prob_over=0.55,
            prob_btts_yes=0.6,
        )
        await session.commit()

    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/dashboard/scores")
    assert resp.status_code == 200
    body = resp.json()

    assert body["model"]["name"] == "ensemble-v1"
    assert len(body["games"]) == 1
    game = body["games"][0]
    assert game["points"] in (0, 50, 100)
    assert game["actual_score"] == "2-1"
    assert "-" in game["predicted_score"]
    assert game["outcome_actual"] == "home"
    # outcome_predicted must be consistent with the predicted scoreline
    ph, pa = (int(x) for x in game["predicted_score"].split("-"))
    expected_outcome = "home" if ph > pa else "away" if ph < pa else "draw"
    assert game["outcome_predicted"] == expected_outcome

    agg = body["aggregate"]
    assert agg["total_games"] == 1
    assert agg["exact"] + agg["outcome_only"] + agg["missed"] == 1
    del client, app
    gc.collect()


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_scores_default_prefers_canonical_model(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """With no ?model, the canonical ensemble-v1 is chosen even when another
    model sorts earlier alphabetically."""
    async with session_factory() as session:
        canonical = await _seed_model(session, name="ensemble-v1", family="ensemble")
        other = await _seed_model(session, name="a-model", family="xgboost")
        for hour, mid in ((18, canonical.id), (20, other.id)):
            await _seed_full_match_with_prediction(
                session,
                model_id=mid,
                kickoff=datetime(2026, 6, 14, hour, 0, tzinfo=UTC),
                score=(2, 1),
                probs_1x2={"home": 0.6, "draw": 0.2, "away": 0.2},
                prob_over=0.55,
                prob_btts_yes=0.6,
            )
        await session.commit()

    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/dashboard/scores")
    assert resp.status_code == 200
    assert resp.json()["model"]["name"] == "ensemble-v1"
    del client, app
    gc.collect()


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_scores_404_when_model_not_found(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """An explicit unknown ?model returns 404."""
    async with session_factory() as session:
        model = await _seed_model(session, name="ensemble-v1", family="ensemble")
        await _seed_full_match_with_prediction(
            session,
            model_id=model.id,
            kickoff=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
            score=(1, 1),
            probs_1x2={"home": 0.4, "draw": 0.4, "away": 0.2},
            prob_over=0.4,
            prob_btts_yes=0.5,
        )
        await session.commit()

    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/dashboard/scores?model=ghost")
    assert resp.status_code == 404
    assert "ghost" in resp.json()["detail"]
    del client, app
    gc.collect()


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_scores_empty_db_returns_404(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """No models at all -> 404."""
    gc.collect()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/dashboard/scores")
    assert resp.status_code == 404
    del client, app
    gc.collect()
