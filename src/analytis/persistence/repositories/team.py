"""Team repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.domain.team import Team, TeamType
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.repositories.base import upsert


def _to_domain(orm: TeamORM) -> Team:
    return Team(
        id=orm.id,
        name=orm.name,
        short_name=orm.short_name,
        team_type=TeamType(orm.team_type),
        country=orm.country,
        external_ids=dict(orm.external_ids),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class TeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, name: str) -> Team | None:
        result = await self._session.scalars(select(TeamORM).where(TeamORM.name == name))
        orm = result.one_or_none()
        return _to_domain(orm) if orm else None

    async def get_by_external_id(self, source: str, ext_id: str) -> Team | None:
        result = await self._session.scalars(
            select(TeamORM).where(TeamORM.external_ids[source].astext == ext_id)
        )
        orm = result.one_or_none()
        return _to_domain(orm) if orm else None

    async def upsert(self, team: Team) -> None:
        await upsert(
            self._session,
            TeamORM,
            values={
                "id": team.id,
                "name": team.name,
                "short_name": team.short_name,
                "team_type": team.team_type.value,
                "country": team.country,
                "external_ids": team.external_ids,
            },
            conflict_cols=["name"],
            update_cols=["short_name", "team_type", "country", "external_ids"],
        )
