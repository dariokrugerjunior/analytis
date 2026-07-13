"""Routes for odds queries."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.config import Settings, get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.odds import OddsSnapshotORM

router = APIRouter(prefix="/matches", tags=["odds"])


@asynccontextmanager
async def _session(settings: Settings) -> AsyncIterator[AsyncSession]:
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


class OddsQuoteResponse(BaseModel):
    bookmaker: str
    market: str
    outcome: str
    decimal_odds: float
    snapshot_taken_at: datetime


class OddsResponse(BaseModel):
    match_id: UUID
    quotes: list[OddsQuoteResponse]
    best_per_outcome: dict[str, dict[str, float | str]]


@router.get(
    "/{match_id}/odds",
    response_model=OddsResponse,
)
async def get_match_odds(
    match_id: UUID,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> OddsResponse:
    async with _session(settings) as session:
        rows = list(
            (
                await session.scalars(
                    select(OddsSnapshotORM).where(OddsSnapshotORM.match_id == match_id)
                )
            ).all()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="no odds for match")

        # Latest per (bookmaker, market, outcome)
        latest: dict[tuple[str, str, str], OddsSnapshotORM] = {}
        for r in rows:
            key = (r.bookmaker, r.market, r.outcome)
            existing = latest.get(key)
            if existing is None or r.snapshot_taken_at > existing.snapshot_taken_at:
                latest[key] = r

        quotes = [
            OddsQuoteResponse(
                bookmaker=r.bookmaker,
                market=r.market,
                outcome=r.outcome,
                decimal_odds=r.decimal_odds,
                snapshot_taken_at=r.snapshot_taken_at,
            )
            for r in latest.values()
        ]

        # Best per outcome across markets
        best: dict[str, dict[str, float | str]] = {}
        for r in latest.values():
            slot = f"{r.market}:{r.outcome}"
            current = best.get(slot)
            current_odds = float(current["decimal_odds"]) if current else 0.0
            if current is None or r.decimal_odds > current_odds:
                best[slot] = {
                    "decimal_odds": r.decimal_odds,
                    "bookmaker": r.bookmaker,
                }

        return OddsResponse(match_id=match_id, quotes=quotes, best_per_outcome=best)
