"""Integration test for the predictions auto-score fallback."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.api.auto_score import auto_score_if_missing
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


async def _seed(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    *,
    narrow_teams: tuple[str, str],
    broad_teams: tuple[str, str, str, str],
    match_home: str,
    match_away: str,
) -> tuple[UUID, UUID, UUID]:
    """Register two DC models (narrow + broad) and a match.

    Returns (match_id, narrow_model_id, broad_model_id).
    """
    async with UnitOfWork(session_factory) as uow:
        crepo = CompetitionRepository(uow.session)
        srepo = SeasonRepository(uow.session)
        trepo = TeamRepository(uow.session)
        mrepo = MatchRepository(uow.session)
        mvrepo = ModelVersionRepository(uow.session)

        comp = Competition(
            name="Auto Score Cup",
            slug="auto-score",
            competition_type=CompetitionType.SELECAO,
            country="INTL",
        )
        await crepo.upsert(comp)
        stored_comp = await crepo.get_by_slug("auto-score")
        assert stored_comp is not None

        season = Season(competition_id=stored_comp.id, label="2026")
        await srepo.upsert(season)
        stored_season = await srepo.get(stored_comp.id, "2026")
        assert stored_season is not None

        all_teams = {*narrow_teams, *broad_teams, match_home, match_away}
        for n in all_teams:
            await trepo.upsert(
                Team(
                    name=n,
                    short_name=n[:5].upper(),
                    team_type=TeamType.SELECAO,
                    country="INT",
                )
            )
        home = await trepo.get_by_name(match_home)
        away = await trepo.get_by_name(match_away)
        assert home is not None
        assert away is not None

        match = Match(
            season_id=stored_season.id,
            home_team_id=home.id,
            away_team_id=away.id,
            kickoff_utc=datetime(2026, 7, 1, 18, 0, tzinfo=UTC),
            is_home_neutral=True,
            status=MatchStatus.SCHEDULED,
            external_ids={"test": "auto-score-target"},
        )
        await mrepo.upsert(match)
        stored_match = await mrepo.get_by_external_id("test", "auto-score-target")
        assert stored_match is not None

        # Narrow model: only the two narrow teams in its roster.
        narrow_params = DixonColesParams(
            attack=dict.fromkeys(narrow_teams, 0.1),
            defense=dict.fromkeys(narrow_teams, -0.1),
            home_advantage=0.2,
            rho=0.0,
        )
        narrow_id = await mvrepo.insert(
            name="dc-narrow",
            family="dixon-coles",
            git_sha="narrow",
            hyperparams={},
            metrics={},
            trained_at=datetime(2026, 6, 1, tzinfo=UTC),
        )
        await uow.session.flush()
        narrow_path = save_params(narrow_params, narrow_id, models_dir=tmp_path)
        narrow_orm = await mvrepo.get(narrow_id)
        assert narrow_orm is not None
        narrow_orm.artifact_path = str(narrow_path)

        # Broad model: covers everything, trained more recently.
        broad_params = DixonColesParams(
            attack=dict.fromkeys(broad_teams, 0.1),
            defense=dict.fromkeys(broad_teams, -0.1),
            home_advantage=0.25,
            rho=-0.02,
        )
        broad_id = await mvrepo.insert(
            name="dc-broad",
            family="dixon-coles",
            git_sha="broad",
            hyperparams={},
            metrics={},
            trained_at=datetime(2026, 6, 10, tzinfo=UTC),
        )
        await uow.session.flush()
        broad_path = save_params(broad_params, broad_id, models_dir=tmp_path)
        broad_orm = await mvrepo.get(broad_id)
        assert broad_orm is not None
        broad_orm.artifact_path = str(broad_path)

    return stored_match.id, narrow_id, broad_id


@pytest.mark.integration
async def test_auto_score_picks_covering_model(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    match_id, _narrow_id, broad_id = await _seed(
        session_factory,
        tmp_path,
        narrow_teams=("Strong-Land", "Weak-Land"),
        broad_teams=("Strong-Land", "Weak-Land", "Iraq", "Norway"),
        match_home="Iraq",
        match_away="Norway",
    )

    model = await auto_score_if_missing(session_factory, match_id)
    assert model is not None
    assert model.id == broad_id

    async with session_factory() as session:
        rows = (
            await session.scalars(select(PredictionORM).where(PredictionORM.match_id == match_id))
        ).all()
    # 3 (1x2) + 2 (OU 2.5) + 2 (BTTS) = 7
    assert len(rows) == 7


@pytest.mark.integration
async def test_auto_score_returns_none_when_no_model_covers(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    match_id, *_ = await _seed(
        session_factory,
        tmp_path,
        narrow_teams=("Strong-Land", "Weak-Land"),
        broad_teams=("Strong-Land", "Weak-Land", "Foo", "Bar"),
        match_home="Iraq",
        match_away="Norway",
    )

    model = await auto_score_if_missing(session_factory, match_id)
    assert model is None

    async with session_factory() as session:
        rows = (
            await session.scalars(select(PredictionORM).where(PredictionORM.match_id == match_id))
        ).all()
    assert rows == []
