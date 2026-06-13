"""Integration test for scoring a match using a fitted DC model."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.score_match import ScoreMatchParams, ScoreMatchUseCase
from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.modeling.fitting import DixonColesParams
from analytis.modeling.persistence import save_params
from analytis.persistence.orm.inference import PredictionORM
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    ModelVersionRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


async def _seed_with_model(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> tuple[Match, UUID]:
    async with UnitOfWork(session_factory) as uow:
        crepo = CompetitionRepository(uow.session)
        srepo = SeasonRepository(uow.session)
        trepo = TeamRepository(uow.session)
        mrepo = MatchRepository(uow.session)
        mvrepo = ModelVersionRepository(uow.session)

        comp = Competition(
            name="Score Test Cup",
            slug="score-test",
            competition_type=CompetitionType.SELECAO,
            country="INTL",
        )
        await crepo.upsert(comp)
        stored_comp = await crepo.get_by_slug("score-test")
        assert stored_comp is not None

        season = Season(competition_id=stored_comp.id, label="2026")
        await srepo.upsert(season)
        stored_season = await srepo.get(stored_comp.id, "2026")
        assert stored_season is not None

        for n in ["Strong-Land", "Weak-Land"]:
            await trepo.upsert(
                Team(
                    name=n,
                    short_name=n[:5].upper(),
                    team_type=TeamType.SELECAO,
                    country="INT",
                )
            )
        strong = await trepo.get_by_name("Strong-Land")
        weak = await trepo.get_by_name("Weak-Land")
        assert strong is not None
        assert weak is not None

        upcoming = Match(
            season_id=stored_season.id,
            home_team_id=strong.id,
            away_team_id=weak.id,
            kickoff_utc=datetime(2026, 6, 20, 18, 0, tzinfo=UTC),
            is_home_neutral=True,
            status=MatchStatus.SCHEDULED,
            external_ids={"test": "score-target"},
        )
        await mrepo.upsert(upcoming)
        stored_match = await mrepo.get_by_external_id("test", "score-target")
        assert stored_match is not None

        # Fit a synthetic model where Strong-Land has higher attack
        # and lower defense (defense is "goals conceded" coefficient — lower = better).
        params = DixonColesParams(
            attack={"Strong-Land": 0.7, "Weak-Land": -0.3},
            defense={"Strong-Land": -0.4, "Weak-Land": 0.5},
            home_advantage=0.2,
            rho=-0.05,
        )
        version_id = await mvrepo.insert(
            name="dc-score-test",
            family="dixon-coles",
            git_sha="testsha",
            hyperparams={"max_iter": 100},
            metrics={},
        )
        await uow.session.flush()
        artifact = save_params(params, version_id, models_dir=tmp_path)
        orm = await mvrepo.get(version_id)
        assert orm is not None
        orm.artifact_path = str(artifact)

    return stored_match, version_id


@pytest.mark.integration
async def test_score_match_creates_predictions(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    stored_match, version_id = await _seed_with_model(session_factory, tmp_path)

    use_case = ScoreMatchUseCase(session_factory)
    result = await use_case.execute(
        ScoreMatchParams(match_id=stored_match.id, model_version_id=version_id)
    )

    # 3 (1x2) + 2 (OU 2.5) + 2 (BTTS) = 7 predictions
    assert result.predictions_inserted == 7

    async with session_factory() as s:
        rows = (
            await s.scalars(select(PredictionORM).where(PredictionORM.match_id == stored_match.id))
        ).all()
        assert len(rows) == 7
        # Home should be a clear favourite given the strong attack and home advantage
        home_prob = next(r.prob for r in rows if r.market == "1x2" and r.outcome == "home")
        away_prob = next(r.prob for r in rows if r.market == "1x2" and r.outcome == "away")
        assert home_prob > away_prob


@pytest.mark.integration
async def test_score_match_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    stored_match, version_id = await _seed_with_model(session_factory, tmp_path)
    use_case = ScoreMatchUseCase(session_factory)

    snap_at = datetime(2026, 6, 19, 12, tzinfo=UTC)
    await use_case.execute(
        ScoreMatchParams(
            match_id=stored_match.id,
            model_version_id=version_id,
            snapshot_taken_at=snap_at,
        )
    )
    await use_case.execute(
        ScoreMatchParams(
            match_id=stored_match.id,
            model_version_id=version_id,
            snapshot_taken_at=snap_at,
        )
    )

    async with session_factory() as s:
        n = await s.scalar(
            select(func.count())
            .select_from(PredictionORM)
            .where(PredictionORM.match_id == stored_match.id)
        )
        assert n == 7  # no duplicates
