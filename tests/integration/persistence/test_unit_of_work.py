"""Integration tests for UnitOfWork."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.persistence.orm import TeamORM
from analytis.persistence.unit_of_work import UnitOfWork


@pytest.mark.integration
async def test_uow_commits_on_success(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with UnitOfWork(session_factory) as u:
        u.session.add(
            TeamORM(
                name="Brazil",
                short_name="BRA",
                team_type="selecao",
                country="BRA",
                external_ids={},
            )
        )

    async with session_factory() as s:
        result = await s.scalars(select(TeamORM).where(TeamORM.name == "Brazil"))
        team = result.one()
        assert team.short_name == "BRA"


@pytest.mark.integration
async def test_uow_rolls_back_on_error(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(RuntimeError, match="boom"):  # noqa: PT012
        async with UnitOfWork(session_factory) as u:
            u.session.add(
                TeamORM(
                    name="Argentina",
                    short_name="ARG",
                    team_type="selecao",
                    country="ARG",
                    external_ids={},
                )
            )
            raise RuntimeError("boom")

    async with session_factory() as s:
        result = await s.scalars(select(TeamORM).where(TeamORM.name == "Argentina"))
        assert result.all() == []
