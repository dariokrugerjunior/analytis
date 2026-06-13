"""Competition repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.domain.competition import Competition, CompetitionType
from analytis.persistence.orm.catalog import CompetitionORM
from analytis.persistence.repositories.base import upsert


def _to_domain(orm: CompetitionORM) -> Competition:
    return Competition(
        id=orm.id,
        name=orm.name,
        slug=orm.slug,
        competition_type=CompetitionType(orm.competition_type),
        country=orm.country,
        external_ids=dict(orm.external_ids),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class CompetitionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_slug(self, slug: str) -> Competition | None:
        result = await self._session.scalars(
            select(CompetitionORM).where(CompetitionORM.slug == slug)
        )
        orm = result.one_or_none()
        return _to_domain(orm) if orm else None

    async def list_all(self) -> list[Competition]:
        result = await self._session.scalars(select(CompetitionORM))
        return [_to_domain(o) for o in result.all()]

    async def upsert(self, competition: Competition) -> None:
        await upsert(
            self._session,
            CompetitionORM,
            values={
                "id": competition.id,
                "name": competition.name,
                "slug": competition.slug,
                "competition_type": competition.competition_type.value,
                "country": competition.country,
                "external_ids": competition.external_ids,
            },
            conflict_cols=["slug"],
            update_cols=["name", "competition_type", "country", "external_ids"],
        )
