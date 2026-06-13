"""Market probability derivations from a Dixon-Coles score matrix.

A score matrix M is (max_goals+1) x (max_goals+1) with
M[i, j] = P(home_goals = i, away_goals = j).
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class MatchResultProbs:
    home: float
    draw: float
    away: float


@dataclass(frozen=True)
class OverUnderProbs:
    over: float
    under: float


@dataclass(frozen=True)
class BttsProbs:
    yes: float
    no: float


def _validate_matrix(matrix: NDArray[np.float64]) -> None:
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("score matrix must be square")


def match_result_probabilities(matrix: NDArray[np.float64]) -> MatchResultProbs:
    _validate_matrix(matrix)
    n = matrix.shape[0]
    home = 0.0
    draw = 0.0
    away = 0.0
    for i in range(n):
        for j in range(n):
            p = float(matrix[i, j])
            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p
    return MatchResultProbs(home=home, draw=draw, away=away)


def over_under_probabilities(matrix: NDArray[np.float64], line: float = 2.5) -> OverUnderProbs:
    _validate_matrix(matrix)
    if abs(line * 2 - round(line * 2)) > 1e-9 or (line * 2) % 2 == 0:
        raise ValueError("over/under line must be a half-integer (e.g. 1.5, 2.5)")
    n = matrix.shape[0]
    over = 0.0
    under = 0.0
    for i in range(n):
        for j in range(n):
            total = i + j
            p = float(matrix[i, j])
            if total > line:
                over += p
            else:
                under += p
    return OverUnderProbs(over=over, under=under)


def btts_probabilities(matrix: NDArray[np.float64]) -> BttsProbs:
    _validate_matrix(matrix)
    n = matrix.shape[0]
    yes = 0.0
    no = 0.0
    for i in range(n):
        for j in range(n):
            p = float(matrix[i, j])
            if i >= 1 and j >= 1:
                yes += p
            else:
                no += p
    return BttsProbs(yes=yes, no=no)


__all__ = [
    "BttsProbs",
    "MatchResultProbs",
    "OverUnderProbs",
    "btts_probabilities",
    "match_result_probabilities",
    "over_under_probabilities",
]
