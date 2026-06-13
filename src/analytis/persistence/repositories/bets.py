"""Repository for ValueBet."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.persistence.orm.bets import ValueBetORM


class ValueBetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        match_id: UUID,
        model_version_id: UUID,
        market: str,
        outcome: str,
        bookmaker: str,
        our_prob: float,
        market_prob: float,
        decimal_odds: float,
        edge: float,
        kelly_fraction: float,
        suggested_stake_units: float,
        found_at: datetime,
    ) -> UUID:
        bet_id = uuid4()
        self._session.add(
            ValueBetORM(
                id=bet_id,
                match_id=match_id,
                model_version_id=model_version_id,
                market=market,
                outcome=outcome,
                bookmaker=bookmaker,
                our_prob=our_prob,
                market_prob=market_prob,
                decimal_odds=decimal_odds,
                edge=edge,
                kelly_fraction=kelly_fraction,
                suggested_stake_units=suggested_stake_units,
                found_at=found_at,
            )
        )
        return bet_id

    async def list_for_match(self, match_id: UUID) -> list[ValueBetORM]:
        result = await self._session.scalars(
            select(ValueBetORM).where(ValueBetORM.match_id == match_id)
        )
        return list(result.all())
