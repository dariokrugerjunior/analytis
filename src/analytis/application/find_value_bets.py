"""Use case: find +EV bets by comparing our predictions to bookmaker odds."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.modeling.ev import edge as compute_edge
from analytis.modeling.kelly import kelly_fraction, kelly_stake_units
from analytis.persistence.orm.inference import PredictionORM
from analytis.persistence.repositories import OddsRepository, ValueBetRepository
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class FindValueBetsParams:
    match_id: UUID
    model_version_id: UUID
    min_edge: float = 0.03
    bankroll: float = 1000.0
    kelly_fraction_value: float = 0.25
    max_units_per_bet: float | None = 50.0


@dataclass
class FindValueBetsResult:
    bets_found: int


class FindValueBetsUseCase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def execute(self, params: FindValueBetsParams) -> FindValueBetsResult:
        async with UnitOfWork(self._factory) as uow:
            preds = (
                await uow.session.scalars(
                    select(PredictionORM).where(
                        PredictionORM.match_id == params.match_id,
                        PredictionORM.model_version_id == params.model_version_id,
                    )
                )
            ).all()
            our_by_outcome: dict[tuple[str, str], PredictionORM] = {
                (p.market, p.outcome): p for p in preds
            }

            odds_repo = OddsRepository(uow.session)
            bets_repo = ValueBetRepository(uow.session)
            now = datetime.now(UTC)

            found = 0
            for market in {p.market for p in preds}:
                latest = await odds_repo.latest_for_match(params.match_id, market)
                best_by_outcome: dict[str, tuple[float, str]] = {}
                for q in latest:
                    cur = best_by_outcome.get(q.outcome)
                    if cur is None or q.decimal_odds > cur[0]:
                        best_by_outcome[q.outcome] = (q.decimal_odds, q.bookmaker)

                for outcome, (best_odds, bm) in best_by_outcome.items():
                    pred = our_by_outcome.get((market, outcome))
                    if pred is None:
                        continue
                    our_prob = pred.prob
                    market_prob = 1.0 / best_odds
                    e = compute_edge(our_prob=our_prob, decimal_odds=best_odds)
                    if e < params.min_edge:
                        continue
                    f = kelly_fraction(our_prob=our_prob, decimal_odds=best_odds)
                    units = kelly_stake_units(
                        our_prob=our_prob,
                        decimal_odds=best_odds,
                        bankroll=params.bankroll,
                        fraction=params.kelly_fraction_value,
                        max_units=params.max_units_per_bet,
                    )
                    await bets_repo.insert(
                        match_id=params.match_id,
                        model_version_id=params.model_version_id,
                        market=market,
                        outcome=outcome,
                        bookmaker=bm,
                        our_prob=our_prob,
                        market_prob=market_prob,
                        decimal_odds=best_odds,
                        edge=e,
                        kelly_fraction=f,
                        suggested_stake_units=units,
                        found_at=now,
                    )
                    found += 1
            return FindValueBetsResult(bets_found=found)
