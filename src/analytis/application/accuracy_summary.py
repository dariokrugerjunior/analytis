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


def actual_1x2(home_goals: int, away_goals: int) -> str:
    """Return actual 1x2 outcome from final scoreline."""
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def actual_ou(home_goals: int, away_goals: int) -> str:
    """Return actual Over/Under outcome from total goals."""
    return "over" if (home_goals + away_goals) > 2.5 else "under"


def actual_btts(home_goals: int, away_goals: int) -> str:
    """Return actual BTTS outcome: both teams scored or not."""
    return "yes" if (home_goals >= 1 and away_goals >= 1) else "no"


def predicted_1x2_top(probs: dict[str, float]) -> tuple[str, float]:
    """Return (top_outcome, top_prob). On a probability tie, the outcome whose
    name comes earlier alphabetically wins."""
    # max with composite key: highest prob wins; on tie, smaller string wins
    # (because we negate via second key — smallest string == "earliest alphabetical").
    # We achieve "smallest string wins" within max() by providing a key that ranks
    # earlier-alphabetical strings as LARGER. Easiest: invert via tuple of negative
    # char codes for the full name.
    return max(probs.items(), key=lambda kv: (kv[1], tuple(-ord(c) for c in kv[0])))


def brier_binary(*, prob: float, outcome: int) -> float:
    """Brier for a single binary prediction. outcome must be 0 or 1."""
    return (prob - outcome) ** 2


def brier_multiclass(*, probs: dict[str, float], actual: str) -> float:
    """Brier multiclass over outcomes. actual is one of probs.keys()."""
    if actual not in probs:
        raise ValueError(f"actual {actual!r} not in probs keys {list(probs)}")
    total = 0.0
    for outcome, p in probs.items():
        y = 1.0 if outcome == actual else 0.0
        total += (p - y) ** 2
    return total / len(probs)


class AccuracySummaryUseCase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def execute(self, params: AccuracySummaryParams) -> AccuracySummary:
        raise NotImplementedError("filled in subsequent tasks")
