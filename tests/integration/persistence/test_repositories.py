"""Integration tests for repositories."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.persistence.repositories import (
    CompetitionRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


@pytest.mark.integration
async def test_competition_upsert_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    c = Competition(
        name="FIFA World Cup 2026",
        slug="wc-2026",
        competition_type=CompetitionType.SELECAO,
        country="INTL",
    )

    async with UnitOfWork(session_factory) as u:
        repo = CompetitionRepository(u.session)
        await repo.upsert(c)

    async with UnitOfWork(session_factory) as u:
        repo = CompetitionRepository(u.session)
        await repo.upsert(c)

    async with session_factory() as s:
        repo = CompetitionRepository(s)
        all_comps = await repo.list_all()
        assert len(all_comps) == 1
        assert all_comps[0].slug == "wc-2026"


@pytest.mark.integration
async def test_team_upsert_updates_existing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    t1 = Team(
        name="Brazil",
        short_name="BRA",
        team_type=TeamType.SELECAO,
        country="BRA",
    )

    async with UnitOfWork(session_factory) as u:
        await TeamRepository(u.session).upsert(t1)

    t2 = Team(
        id=t1.id,
        name="Brazil",
        short_name="BRA",
        team_type=TeamType.SELECAO,
        country="BRA",
        external_ids={"footballdata": "764"},
    )
    async with UnitOfWork(session_factory) as u:
        await TeamRepository(u.session).upsert(t2)

    async with session_factory() as s:
        team = await TeamRepository(s).get_by_external_id("footballdata", "764")
        assert team is not None
        assert team.name == "Brazil"


@pytest.mark.integration
async def test_season_upsert(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    c = Competition(
        name="FIFA World Cup 2026",
        slug="wc-2026",
        competition_type=CompetitionType.SELECAO,
        country="INTL",
    )
    async with UnitOfWork(session_factory) as u:
        await CompetitionRepository(u.session).upsert(c)

    s = Season(competition_id=c.id, label="2026")
    async with UnitOfWork(session_factory) as u:
        await SeasonRepository(u.session).upsert(s)

    async with session_factory() as sess:
        got = await SeasonRepository(sess).get(c.id, "2026")
        assert got is not None
        assert got.label == "2026"
