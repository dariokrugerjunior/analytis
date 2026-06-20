"""Use case for computing model accuracy on finished matches with predictions."""

from __future__ import annotations

import math
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


_PHASE_MAP: dict[str, Phase] = {
    "GROUP_STAGE": "group",
    "LAST_16": "round_of_16",
    "QUARTER_FINALS": "quarterfinal",
    "SEMI_FINALS": "semifinal",
    "THIRD_PLACE": "semifinal",
    "FINAL": "final",
}


def normalize_phase(competition_round: str | None) -> Phase:
    """Map Football-Data competition_round string to our canonical Phase."""
    if competition_round is None:
        return "group"
    return _PHASE_MAP.get(competition_round, "group")


def wilson_ci(*, hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% by default).

    Returns (low, high) clipped to [0.0, 1.0]. When n == 0 returns (0.0, 1.0).
    """
    if n <= 0:
        return (0.0, 1.0)
    p = hits / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    low = max(0.0, center - half)
    high = min(1.0, center + half)
    return (low, high)


class AccuracySummaryUseCase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def execute(self, params: AccuracySummaryParams) -> AccuracySummary:
        raise NotImplementedError("filled in subsequent tasks")
