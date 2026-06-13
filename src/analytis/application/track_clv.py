"""Use case: update CLV (closing-line value) on ValueBet rows."""

import math
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.persistence.orm.bets import ValueBetORM
from analytis.persistence.repositories import OddsRepository
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class TrackCLVParams:
    match_id: UUID


@dataclass
class TrackCLVResult:
    bets_updated: int


class TrackCLVUseCase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def execute(self, params: TrackCLVParams) -> TrackCLVResult:
        async with UnitOfWork(self._factory) as uow:
            bets = (
                await uow.session.scalars(
                    select(ValueBetORM).where(ValueBetORM.match_id == params.match_id)
                )
            ).all()
            odds_repo = OddsRepository(uow.session)
            updated = 0
            for bet in bets:
                latest = await odds_repo.latest_for_match(params.match_id, bet.market)
                same = [
                    q for q in latest if q.bookmaker == bet.bookmaker and q.outcome == bet.outcome
                ]
                if not same:
                    continue
                closing = max(same, key=lambda q: q.snapshot_taken_at)
                if closing.snapshot_taken_at <= bet.found_at:
                    continue
                bet.closing_decimal_odds = closing.decimal_odds
                bet.closing_clv = math.log(bet.decimal_odds / closing.decimal_odds)
                updated += 1
            return TrackCLVResult(bets_updated=updated)
