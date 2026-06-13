"""Routes for match predictions."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.api.deps import require_api_key
from analytis.config import Settings, get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.inference import ModelVersionORM, PredictionORM
from analytis.persistence.orm.matches import MatchORM

router = APIRouter(prefix="/matches", tags=["predictions"])


@asynccontextmanager
async def _session(settings: Settings) -> AsyncIterator[AsyncSession]:
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


class PredictionResponse(BaseModel):
    market: str
    outcome: str
    prob: float
    ci_low: float
    ci_high: float
    model_version: str
    created_at: datetime


class MatchPredictionsResponse(BaseModel):
    match_id: UUID
    home_goals: int | None
    away_goals: int | None
    status: str
    kickoff_utc: datetime
    predictions: list[PredictionResponse]


@router.get(
    "/{match_id}/predictions",
    response_model=MatchPredictionsResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_match_predictions(
    match_id: UUID,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> MatchPredictionsResponse:
    async with _session(settings) as session:
        match = await session.get(MatchORM, match_id)
        if match is None:
            raise HTTPException(status_code=404, detail="match not found")

        stmt = (
            select(PredictionORM, ModelVersionORM.name)
            .join(
                ModelVersionORM,
                PredictionORM.model_version_id == ModelVersionORM.id,
            )
            .where(PredictionORM.match_id == match_id)
            .order_by(PredictionORM.created_at.desc(), PredictionORM.market)
        )
        rows = (await session.execute(stmt)).all()

        items = [
            PredictionResponse(
                market=row[0].market,
                outcome=row[0].outcome,
                prob=row[0].prob,
                ci_low=row[0].ci_low,
                ci_high=row[0].ci_high,
                model_version=row[1],
                created_at=row[0].created_at,
            )
            for row in rows
        ]

        return MatchPredictionsResponse(
            match_id=match.id,
            home_goals=match.home_goals,
            away_goals=match.away_goals,
            status=match.status,
            kickoff_utc=match.kickoff_utc,
            predictions=items,
        )
