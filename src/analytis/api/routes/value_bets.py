"""Routes for value bets + CLV summary."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.api.deps import require_api_key
from analytis.config import Settings, get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.bets import ValueBetORM
from analytis.persistence.orm.inference import ModelVersionORM

router = APIRouter(tags=["value_bets"])


@asynccontextmanager
async def _session(settings: Settings) -> AsyncIterator[AsyncSession]:
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


class ValueBetResponse(BaseModel):
    id: UUID
    match_id: UUID
    model_version_id: UUID
    market: str
    outcome: str
    bookmaker: str
    our_prob: float
    market_prob: float
    decimal_odds: float
    edge: float
    kelly_fraction: float
    suggested_stake_units: float
    found_at: datetime
    closing_decimal_odds: float | None
    closing_clv: float | None


class ValueBetsList(BaseModel):
    items: list[ValueBetResponse]


@router.get(
    "/matches/{match_id}/value-bets",
    response_model=ValueBetsList,
    dependencies=[Depends(require_api_key)],
)
async def get_match_value_bets(
    match_id: UUID,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> ValueBetsList:
    async with _session(settings) as session:
        rows = list(
            (
                await session.scalars(select(ValueBetORM).where(ValueBetORM.match_id == match_id))
            ).all()
        )
        items = [
            ValueBetResponse(
                id=b.id,
                match_id=b.match_id,
                model_version_id=b.model_version_id,
                market=b.market,
                outcome=b.outcome,
                bookmaker=b.bookmaker,
                our_prob=b.our_prob,
                market_prob=b.market_prob,
                decimal_odds=b.decimal_odds,
                edge=b.edge,
                kelly_fraction=b.kelly_fraction,
                suggested_stake_units=b.suggested_stake_units,
                found_at=b.found_at,
                closing_decimal_odds=b.closing_decimal_odds,
                closing_clv=b.closing_clv,
            )
            for b in rows
        ]
        return ValueBetsList(items=items)


class CLVSummary(BaseModel):
    model_version: str
    n_bets: int
    n_with_clv: int
    mean_clv: float | None
    median_edge: float | None


class CLVSummaryList(BaseModel):
    items: list[CLVSummary]


@router.get(
    "/bets/clv-summary",
    response_model=CLVSummaryList,
    dependencies=[Depends(require_api_key)],
)
async def get_clv_summary(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> CLVSummaryList:
    async with _session(settings) as session:
        rows = list(
            (
                await session.execute(
                    select(
                        ModelVersionORM.name,
                        func.count(ValueBetORM.id).label("n_bets"),
                        func.count(ValueBetORM.closing_clv).label("n_with_clv"),
                        func.avg(ValueBetORM.closing_clv).label("mean_clv"),
                        func.percentile_cont(0.5)
                        .within_group(ValueBetORM.edge)
                        .label("median_edge"),
                    )
                    .join(
                        ValueBetORM,
                        ValueBetORM.model_version_id == ModelVersionORM.id,
                    )
                    .group_by(ModelVersionORM.name)
                )
            ).all()
        )
        items = [
            CLVSummary(
                model_version=row.name,
                n_bets=int(row.n_bets or 0),
                n_with_clv=int(row.n_with_clv or 0),
                mean_clv=float(row.mean_clv) if row.mean_clv is not None else None,
                median_edge=(float(row.median_edge) if row.median_edge is not None else None),
            )
            for row in rows
        ]
        return CLVSummaryList(items=items)
