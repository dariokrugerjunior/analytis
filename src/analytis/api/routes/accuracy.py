"""GET /v1/accuracy/summary endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from analytis.application.accuracy_summary import (
    AccuracySummary,
    AccuracySummaryParams,
    AccuracySummaryUseCase,
    ModelNotFoundError,
)
from analytis.config import Settings, get_settings
from analytis.persistence.engine import create_engine, create_session_factory

router = APIRouter(
    prefix="/accuracy",
    tags=["accuracy"],
)


def _use_case(settings: Settings) -> AccuracySummaryUseCase:
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    return AccuracySummaryUseCase(factory)


@router.get("/summary", response_model=AccuracySummary)
async def get_accuracy_summary(
    model: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> AccuracySummary:
    use_case = _use_case(settings)
    try:
        return await use_case.execute(AccuracySummaryParams(model_name=model))
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
