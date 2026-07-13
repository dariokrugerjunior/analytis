"""Use case for the dashboard home screen: a per-game accuracy *score*.

Each finished match that has a model prediction is graded with a single,
easy-to-read points value derived from the predicted scoreline:

* predicted **exact score == actual score** -> **100** points
  (this already covers an exactly-correct draw);
* else if predicted **outcome == actual outcome** (correct winner, or correctly
  a draw) but the scoreline differs -> **50** points;
* else (wrong outcome) -> **0** points.

The heavy lifting (loading finished matches, deriving the most-likely scoreline
from the ensemble marginals or a Dixon-Coles artifact) is already implemented by
``AccuracySummaryUseCase``; this use case reuses it and reshapes its output into
the compact per-game score list the dashboard needs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.accuracy_summary import (
    AccuracySummary,
    AccuracySummaryParams,
    AccuracySummaryUseCase,
    MatchRow,
    ModelNotFoundError,
    ModelOption,
    ModelRef,
    actual_1x2,
)

#: The model the dashboard pins by default. Mirrors ``scoreline.py`` /
#: ``frontend/src/lib/models.ts``.
CANONICAL_MODEL = "ensemble-v1"

EXACT_POINTS = 100
OUTCOME_POINTS = 50
MISS_POINTS = 0


def match_points(pred_home: int, pred_away: int, actual_home: int, actual_away: int) -> int:
    """Grade a single match per the dashboard scoring rule.

    Returns 100 for an exact scoreline (including an exactly-correct draw),
    50 for a correct outcome (winner or draw) with the wrong scoreline, and
    0 for a wrong outcome.
    """
    if pred_home == actual_home and pred_away == actual_away:
        return EXACT_POINTS
    if actual_1x2(pred_home, pred_away) == actual_1x2(actual_home, actual_away):
        return OUTCOME_POINTS
    return MISS_POINTS


class DashboardGame(BaseModel):
    match_id: UUID
    home_team: str
    away_team: str
    kickoff_utc: datetime
    predicted_score: str  # e.g. "2-1"
    actual_score: str  # e.g. "2-1"
    outcome_predicted: str  # "home" | "draw" | "away"
    outcome_actual: str  # "home" | "draw" | "away"
    points: int  # 0 | 50 | 100


class DashboardAggregate(BaseModel):
    total_games: int
    avg_points: float
    exact: int  # games worth 100
    outcome_only: int  # games worth 50
    missed: int  # games worth 0


class DashboardScores(BaseModel):
    model: ModelRef
    available_models: list[ModelOption]
    aggregate: DashboardAggregate
    games: list[DashboardGame]


@dataclass
class DashboardScoresParams:
    model_name: str | None = None


def _game_from_row(row: MatchRow) -> DashboardGame | None:
    """Build a graded game from an accuracy MatchRow, or None when the model
    could not derive a most-likely scoreline for the match."""
    pred_home = row.scoreline_predicted_home
    pred_away = row.scoreline_predicted_away
    if pred_home is None or pred_away is None:
        return None
    points = match_points(pred_home, pred_away, row.home_goals, row.away_goals)
    return DashboardGame(
        match_id=row.match_id,
        home_team=row.home_team,
        away_team=row.away_team,
        kickoff_utc=row.kickoff_utc,
        predicted_score=f"{pred_home}-{pred_away}",
        actual_score=f"{row.home_goals}-{row.away_goals}",
        outcome_predicted=actual_1x2(pred_home, pred_away),
        outcome_actual=actual_1x2(row.home_goals, row.away_goals),
        points=points,
    )


def build_games(matches: list[MatchRow]) -> list[DashboardGame]:
    """Grade every match that has a derivable scoreline, chronologically."""
    games = [g for g in (_game_from_row(r) for r in matches) if g is not None]
    games.sort(key=lambda g: g.kickoff_utc)
    return games


def build_aggregate(games: list[DashboardGame]) -> DashboardAggregate:
    """Summarise the graded games into headline KPIs."""
    total = len(games)
    exact = sum(1 for g in games if g.points == EXACT_POINTS)
    outcome_only = sum(1 for g in games if g.points == OUTCOME_POINTS)
    missed = sum(1 for g in games if g.points == MISS_POINTS)
    avg = (sum(g.points for g in games) / total) if total else 0.0
    return DashboardAggregate(
        total_games=total,
        avg_points=avg,
        exact=exact,
        outcome_only=outcome_only,
        missed=missed,
    )


class DashboardScoresUseCase:
    """Compute the per-game score dashboard for one model."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._accuracy = AccuracySummaryUseCase(session_factory)

    async def execute(self, params: DashboardScoresParams) -> DashboardScores:
        summary = await self._resolve_summary(params.model_name)
        games = build_games(summary.matches)
        return DashboardScores(
            model=summary.model,
            available_models=summary.available_models,
            aggregate=build_aggregate(games),
            games=games,
        )

    async def _resolve_summary(self, model_name: str | None) -> AccuracySummary:
        """Pick the model: an explicit request is honoured; otherwise pin the
        canonical model, falling back to the accuracy default (first
        alphabetical with predictions) when it isn't available."""
        if model_name is not None:
            return await self._accuracy.execute(AccuracySummaryParams(model_name=model_name))
        try:
            return await self._accuracy.execute(AccuracySummaryParams(model_name=CANONICAL_MODEL))
        except ModelNotFoundError:
            return await self._accuracy.execute(AccuracySummaryParams(model_name=None))
