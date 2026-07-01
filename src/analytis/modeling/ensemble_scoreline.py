"""Derive a Poisson scoreline distribution from an ensemble model's marginals.

The ensemble ships P(1X2) and P(over 2.5) as probabilities but no joint score
distribution. Fitting an independent-Poisson grid whose marginals reproduce
those probabilities gives a coherent "most likely score" view that never
contradicts the 1X2 bars on the same screen.
"""

from __future__ import annotations

import numpy as np
from scipy import stats
from scipy.optimize import brentq


def derive_lambdas(
    p_home_win: float, p_over_2_5: float, max_goals: int = 10
) -> tuple[float, float]:
    """Solve for λ_home, λ_away (two independent Poissons) whose marginals
    reproduce the ensemble's P(home wins) and P(over 2.5 goals).

    Two constraints, two unknowns:
      1. μ = λ_h + λ_a solved from 1 - P(H+A ≤ 2 | Poisson(μ)) = p_over_2_5
         (sum of independent Poissons is Poisson).
      2. λ_h solved from Σ_{i≥1} P(H=i) · P(A ≤ i-1) = p_home_win, given μ.
    """

    def over_gap(mu: float) -> float:
        return float(1.0 - stats.poisson.cdf(2, mu)) - p_over_2_5

    try:
        mu = brentq(over_gap, 0.05, 15.0, xtol=1e-4)
    except ValueError:
        mu = 2.5

    ks = np.arange(max_goals + 1)

    def home_win_gap(lam_h: float) -> float:
        lam_a = max(mu - lam_h, 1e-6)
        h_pmf = stats.poisson.pmf(ks, lam_h)
        a_pmf = stats.poisson.pmf(ks, lam_a)
        cdf_a = np.cumsum(a_pmf)
        p_h = float(np.sum(h_pmf[1:] * cdf_a[:-1]))
        return p_h - p_home_win

    try:
        lam_h = brentq(home_win_gap, 1e-4, mu - 1e-4, xtol=1e-4)
    except ValueError:
        lam_h = mu / 2.0

    return float(lam_h), float(mu - lam_h)


def score_matrix(lam_h: float, lam_a: float, max_goals: int) -> np.ndarray:
    """Independent Poisson joint distribution over (H, A) up to max_goals."""
    ks = np.arange(max_goals + 1)
    h_pmf = stats.poisson.pmf(ks, lam_h)
    a_pmf = stats.poisson.pmf(ks, lam_a)
    return np.outer(h_pmf, a_pmf)


def most_likely_score(lam_h: float, lam_a: float, max_goals: int = 10) -> tuple[int, int]:
    """argmax_{i,j} P(H=i, A=j) over an independent Poisson grid."""
    matrix = score_matrix(lam_h, lam_a, max_goals)
    idx = int(np.argmax(matrix))
    home, away = divmod(idx, int(matrix.shape[1]))
    return int(home), int(away)
