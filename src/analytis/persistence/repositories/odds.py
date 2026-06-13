"""Repository for OddsSnapshot."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.persistence.orm.odds import OddsSnapshotORM


class OddsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_quote(
        self,
        *,
        match_id: UUID,
        bookmaker: str,
        market: str,
        outcome: str,
        decimal_odds: float,
        snapshot_taken_at: datetime,
    ) -> bool:
        """Insert if (match, bm, market, outcome, taken_at) is new; else no-op.
        Returns True if a row was actually inserted."""
        base_stmt = pg_insert(OddsSnapshotORM).values(
            match_id=match_id,
            bookmaker=bookmaker,
            market=market,
            outcome=outcome,
            decimal_odds=decimal_odds,
            snapshot_taken_at=snapshot_taken_at,
        )
        stmt = base_stmt.on_conflict_do_nothing(constraint="uq_odds_snapshot_natural").returning(
            OddsSnapshotORM.id
        )
        result = await self._session.execute(stmt)
        return result.scalar() is not None

    async def latest_for_match(self, match_id: UUID, market: str) -> list[OddsSnapshotORM]:
        result = await self._session.scalars(
            select(OddsSnapshotORM).where(
                OddsSnapshotORM.match_id == match_id,
                OddsSnapshotORM.market == market,
            )
        )
        rows = list(result.all())
        latest_per_book: dict[tuple[str, str], OddsSnapshotORM] = {}
        for r in rows:
            key = (r.bookmaker, r.outcome)
            existing = latest_per_book.get(key)
            if existing is None or r.snapshot_taken_at > existing.snapshot_taken_at:
                latest_per_book[key] = r
        return list(latest_per_book.values())
