"""Repository for ELO history."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.domain.elo import EloRating
from analytis.persistence.orm.elo import EloHistoryORM


def _to_domain(orm: EloHistoryORM) -> EloRating:
    return EloRating(
        id=orm.id,
        team_id=orm.team_id,
        rating=orm.rating,
        as_of=orm.as_of,
        games_played=orm.games_played,
    )


class EloHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest_for_team(self, team_id: UUID, as_of: datetime) -> EloRating | None:
        result = await self._session.scalars(
            select(EloHistoryORM)
            .where(
                EloHistoryORM.team_id == team_id,
                EloHistoryORM.as_of <= as_of,
            )
            .order_by(EloHistoryORM.as_of.desc())
            .limit(1)
        )
        orm = result.one_or_none()
        return _to_domain(orm) if orm else None

    async def insert(self, rating: EloRating) -> None:
        self._session.add(
            EloHistoryORM(
                id=rating.id,
                team_id=rating.team_id,
                rating=rating.rating,
                as_of=rating.as_of,
                games_played=rating.games_played,
            )
        )

    async def clear_all(self) -> None:
        await self._session.execute(delete(EloHistoryORM))
