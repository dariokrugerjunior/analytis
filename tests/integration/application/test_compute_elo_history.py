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
            name="FIFA World Cup",
            slug="fifa-world-cup-history",
            competition_type=CompetitionType.SELECAO,
            country="INTL",
        )
        await crepo.upsert(comp)
        stored_comp = await crepo.get_by_slug("fifa-world-cup-history")
        assert stored_comp is not None
        season = Season(competition_id=stored_comp.id, label="2018")
        await srepo.upsert(season)
        stored_season = await srepo.get(stored_comp.id, "2018")
        assert stored_season is not None
        for n in ["Brazil", "Mexico", "Belgium"]:
            await trepo.upsert(
                Team(
                    name=n,
                    short_name=n[:5].upper(),
                    team_type=TeamType.SELECAO,
                    country="INT",
                )
            )
        bra = await trepo.get_by_name("Brazil")
        mex = await trepo.get_by_name("Mexico")
        bel = await trepo.get_by_name("Belgium")
        assert bra is not None
        assert mex is not None
        assert bel is not None
        for ext, (h, a, hg, ag, when) in enumerate(
            [
                (bra.id, mex.id, 2, 0, datetime(2018, 7, 2, 12, tzinfo=UTC)),
                (bel.id, bra.id, 2, 1, datetime(2018, 7, 6, 12, tzinfo=UTC)),
            ]
        ):
            await mrepo.upsert(
                Match(
                    season_id=stored_season.id,
                    home_team_id=h,
                    away_team_id=a,
                    kickoff_utc=when,
                    is_home_neutral=True,
                    status=MatchStatus.FINISHED,
                    home_goals=hg,
                    away_goals=ag,
                    external_ids={"test": f"m{ext}"},
                )
            )


@pytest.mark.integration
async def test_compute_elo_history_basic(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed_minimal(session_factory)
    use_case = ComputeEloHistoryUseCase(session_factory)
    result = await use_case.execute()
    assert result.teams_seen == 3
    assert result.ratings_written == 4  # 2 matches x 2 teams

    async with session_factory() as s:
        count = await s.scalar(select(func.count()).select_from(EloHistoryORM))
        assert count == 4
