"""Dixon-Coles bivariate Poisson model — math primitives.

References:
    Dixon, M. J., & Coles, S. G. (1997). Modelling association football scores
    and inefficiencies in the football betting market. Journal of the Royal
    Statistical Society: Series C (Applied Statistics), 46(2), 265-280.

This module is pure math: no I/O, no state. The fitter (T14) calls these to
build a log-likelihood objective; the market derivations (T15) use score_matrix.
"""

import math

import numpy as np
from numpy.typing import NDArray


def tau(
    home_goals: int,
    away_goals: int,
    lambda_home: float,
    lambda_away: float,
    rho: float,
) -> float:
    """Low-score correction factor.

    Returns 1.0 for any (i, j) outside the 2x2 grid {0,1} x {0,1}, where the
    independent-Poisson assumption breaks down for football scores.
    """
    if home_goals == 0 and away_goals == 0:
        return 1.0 - lambda_home * lambda_away * rho
    if home_goals == 0 and away_goals == 1:
        return 1.0 + lambda_home * rho
    if home_goals == 1 and away_goals == 0:
        return 1.0 + lambda_away * rho
    if home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    return 1.0


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam**k) / math.factorial(k)


def score_matrix(
    lambda_home: float,
    lambda_away: float,
    rho: float,
    max_goals: int = 10,
) -> NDArray[np.float64]:
    """Build a (max_goals+1) x (max_goals+1) probability matrix of exact scores.

    M[i, j] = P(home_goals = i, away_goals = j).
    """
    if lambda_home <= 0 or lambda_away <= 0:
        raise ValueError("lambda must be positive")
    if max_goals < 1:
        raise ValueError("max_goals must be >= 1")

    n = max_goals + 1
    home_pmf = np.array([_poisson_pmf(i, lambda_home) for i in range(n)])
    away_pmf = np.array([_poisson_pmf(j, lambda_away) for j in range(n)])

    matrix = np.outer(home_pmf, away_pmf)
    # Apply Dixon-Coles correction only to the 2x2 low-score grid.
    for i in (0, 1):
        for j in (0, 1):
            matrix[i, j] *= tau(i, j, lambda_home, lambda_away, rho)
    return matrix


def log_likelihood_match(
    home_goals: int,
    away_goals: int,
    lambda_home: float,
    lambda_away: float,
    rho: float,
) -> float:
    """Log-likelihood of a single observed match under Dixon-Coles."""
    if lambda_home <= 0 or lambda_away <= 0:
        raise ValueError("lambda must be positive")
    correction = tau(home_goals, away_goals, lambda_home, lambda_away, rho)
    if correction <= 0:
        raise ValueError("DC correction <= 0 — rho out of valid range")
    base = (
        -lambda_home
        + home_goals * math.log(lambda_home)
        - math.log(math.factorial(home_goals))
        - lambda_away
        + away_goals * math.log(lambda_away)
        - math.log(math.factorial(away_goals))
    )
    return base + math.log(correction)


__all__ = ["log_likelihood_match", "score_matrix", "tau"]
