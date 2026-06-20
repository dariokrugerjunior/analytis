"""Use case for computing model accuracy on finished matches with predictions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

Phase = Literal["group", "round_of_16", "quarterfinal", "semifinal", "final"]
PHASES: tuple[Phase, ...] = ("group", "round_of_16", "quarterfinal", "semifinal", "final")


class ModelRef(BaseModel):
    id: UUID
    name: str
    family: str


class ModelOption(ModelRef):
    n_predictions: int


class MarketKpi(BaseModel):
    hits: int
    n: int
    rate: float
    ci_low: float
    ci_high: float
    brier_avg: float


class Kpis(BaseModel):
    n_matches_evaluated: int
    markets: dict[str, MarketKpi]  # keys: "1x2", "ou", "btts"
    brier_overall: float


class TimeseriesPoint(BaseModel):
    phase: Phase
    n: int
    cumulative: dict[str, float]  # keys: "1x2", "ou", "btts"


class MatchPredictionDetail(BaseModel):
    predicted: str
    predicted_prob: float
    actual: str
    hit: bool
    brier: float


class MatchRow(BaseModel):
    match_id: UUID
    kickoff_utc: datetime
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    phase: Phase
    predictions: dict[str, MatchPredictionDetail]  # keys: "1x2", "ou", "btts"


class AccuracySummary(BaseModel):
    model: ModelRef
    available_models: list[ModelOption]
    kpis: Kpis
    timeseries: list[TimeseriesPoint]
    matches: list[MatchRow]


@dataclass
class AccuracySummaryParams:
    model_name: str | None


class ModelNotFoundError(Exception):
    """Raised when ?model=<name> doesn't match any model_version with predictions."""


class AccuracySummaryUseCase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def execute(self, params: AccuracySummaryParams) -> AccuracySummary:
        raise NotImplementedError("filled in subsequent tasks")
