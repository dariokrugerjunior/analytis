"""Match-context features: rest days, stage (eliminatorio?), H2H summaries.

Pure functions; the builder (T12) prepares inputs.
"""

from dataclasses import dataclass
from datetime import datetime

_ELIMINATION_STAGES: frozenset[str] = frozenset(
    {
        "ROUND_OF_16",
        "QUARTER_FINALS",
        "SEMI_FINALS",
        "FINAL",
        "THIRD_PLACE",
        "PLAYOFFS",
        "PRELIMINARY_ROUND",
        "LAST_16",
    }
)


@dataclass(frozen=True)
class H2HSample:
    """A historical head-to-head match.

    home_goals/away_goals are relative to the *current* match's home team.
    The builder is responsible for normalising past matches to that frame.
    """

    home_goals: int
    away_goals: int


def rest_days(*, last_match_at: datetime | None, current_match_at: datetime) -> int | None:
    if last_match_at is None:
        return None
    if last_match_at > current_match_at:
        raise ValueError("last_match_at must be before current_match_at")
    delta = current_match_at - last_match_at
    return delta.days


def is_elimination_stage(stage: str | None) -> bool:
    if not stage:
        return False
    return stage.strip().upper() in _ELIMINATION_STAGES


def _outcome_score(home_goals: int, away_goals: int) -> float:
    if home_goals > away_goals:
        return 1.0
    if home_goals < away_goals:
        return 0.0
    return 0.5


def h2h_home_win_rate(*, history: list[H2HSample]) -> float | None:
    if not history:
        return None
    total = sum(_outcome_score(s.home_goals, s.away_goals) for s in history)
    return total / len(history)


def h2h_total_goals_avg(*, history: list[H2HSample]) -> float | None:
    if not history:
        return None
    total = sum(s.home_goals + s.away_goals for s in history)
    return total / len(history)


__all__ = [
    "H2HSample",
    "h2h_home_win_rate",
    "h2h_total_goals_avg",
    "is_elimination_stage",
    "rest_days",
]
