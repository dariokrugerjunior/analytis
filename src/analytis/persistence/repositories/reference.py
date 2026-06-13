"""Season repository (and other simple referential repos)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.domain.ids import CompetitionId
from analytis.domain.season import Season
from analytis.persistence.orm.catalog import SeasonORM
from analytis.persistence.repositories.base import upsert


def _to_domain(orm: SeasonORM) -> Season:
    return Season(
        id=orm.id,
        competition_id=orm.competition_id,
        label=orm.label,
        start_date=orm.start_date,
        end_date=orm.end_date,
        external_ids=dict(orm.external_ids),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SeasonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, competition_id: CompetitionId, label: str) -> Season | None:
        result = await self._session.scalars(
            select(SeasonORM).where(
                SeasonORM.competition_id == competition_id,
                SeasonORM.label == label,
            )
        )
        orm = result.one_or_none()
        return _to_domain(orm) if orm else None

    async def upsert(self, season: Season) -> None:
        await upsert(
            self._session,
            SeasonORM,
            values={
                "id": season.id,
                "competition_id": season.competition_id,
                "label": season.label,
                "start_date": season.start_date,
                "end_date": season.end_date,
                "external_ids": season.external_ids,
            },
            conflict_cols=["competition_id", "label"],
            update_cols=["start_date", "end_date", "external_ids"],
        )
