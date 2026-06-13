"""Recent-form features.

History is a list of FormSample, ORDERED MOST-RECENT FIRST. Each sample
gets weight w_i = exp(-decay * i). Result = sum(w_i * value_i) / sum(w_i).
When history is empty, the functions return None.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class FormSample:
    goals_for: int
    goals_against: int


def _validate(decay: float, window: int) -> None:
    if decay < 0:
        raise ValueError("decay must be non-negative")
    if window <= 0:
        raise ValueError("window must be positive")


def _weighted_avg(
    samples: list[FormSample],
    decay: float,
    window: int,
    extractor: Callable[[FormSample], float],
) -> float | None:
    if not samples:
        return None
    truncated = samples[:window]
    numerator = 0.0
    denominator = 0.0
    for i, s in enumerate(truncated):
        w = math.exp(-decay * i)
        numerator += w * extractor(s)
        denominator += w
    return numerator / denominator


def form_goals_for(*, history: list[FormSample], decay: float, window: int = 10) -> float | None:
    _validate(decay, window)
    return _weighted_avg(history, decay, window, lambda s: float(s.goals_for))


def form_goals_against(
    *, history: list[FormSample], decay: float, window: int = 10
) -> float | None:
    _validate(decay, window)
    return _weighted_avg(history, decay, window, lambda s: float(s.goals_against))


def form_goal_diff(*, history: list[FormSample], decay: float, window: int = 10) -> float | None:
    _validate(decay, window)
    return _weighted_avg(history, decay, window, lambda s: float(s.goals_for - s.goals_against))


__all__ = [
    "FormSample",
    "form_goal_diff",
    "form_goals_against",
    "form_goals_for",
]
