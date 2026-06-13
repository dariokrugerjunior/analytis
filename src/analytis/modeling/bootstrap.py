"""Bootstrap resampling for Dixon-Coles parameter uncertainty.

For each bootstrap sample, draw N matches with replacement from the input
list and refit. Use the spread of per-match market probabilities across
samples as a credible interval.
"""

import math
import random
from dataclasses import dataclass

import numpy as np

from analytis.modeling.dixon_coles import score_matrix
from analytis.modeling.fitting import (
    DixonColesParams,
    FitConfig,
    MatchObservation,
    fit_dixon_coles,
)
from analytis.modeling.markets import (
    btts_probabilities,
    match_result_probabilities,
    over_under_probabilities,
)


@dataclass
class BootstrapResult:
    samples: list[DixonColesParams]


def bootstrap_fit(
    matches: list[MatchObservation],
    *,
    n_samples: int = 50,
    max_iter: int = 200,
    decay_per_day: float = 0.0,
    seed: int | None = None,
) -> BootstrapResult:
    if n_samples <= 0:
        raise ValueError("n_samples must be positive")
    rng = random.Random(seed)
    samples: list[DixonColesParams] = []
    n = len(matches)
    for _ in range(n_samples):
        drawn = [matches[rng.randrange(n)] for _ in range(n)]
        try:
            fit = fit_dixon_coles(
                drawn,
                config=FitConfig(max_iter=max_iter, decay_per_day=decay_per_day),
            )
            samples.append(fit)
        except ValueError:
            continue
    return BootstrapResult(samples=samples)


def _market_prob_for_sample(
    params: DixonColesParams,
    home_team: str,
    away_team: str,
    market: str,
    outcome: str,
    is_neutral: bool,
) -> float:
    if home_team not in params.attack:
        raise KeyError(f"{home_team} missing in sample")
    if away_team not in params.attack:
        raise KeyError(f"{away_team} missing in sample")
    ha = 0.0 if is_neutral else params.home_advantage
    lam_h = math.exp(params.attack[home_team] - params.defense[away_team] + ha)
    lam_a = math.exp(params.attack[away_team] - params.defense[home_team])
    matrix = score_matrix(lam_h, lam_a, params.rho, max_goals=10)
    if market == "1x2":
        mr = match_result_probabilities(matrix)
        return {"home": mr.home, "draw": mr.draw, "away": mr.away}[outcome]
    if market == "over_under_goals":
        ou = over_under_probabilities(matrix, line=2.5)
        return ou.over if outcome.startswith("over") else ou.under
    if market == "btts":
        bt = btts_probabilities(matrix)
        return bt.yes if outcome == "yes" else bt.no
    raise ValueError(f"unknown market {market!r}")


def market_ci_from_samples(
    samples: list[DixonColesParams],
    *,
    home_team: str,
    away_team: str,
    market: str,
    outcome: str,
    is_neutral: bool,
    ci_level: float = 0.95,
) -> tuple[float, float, float]:
    """Returns (point_estimate, ci_low, ci_high) using percentiles."""
    if not samples:
        raise ValueError("samples must not be empty")
    probs = [
        _market_prob_for_sample(s, home_team, away_team, market, outcome, is_neutral)
        for s in samples
    ]
    arr = np.array(probs, dtype=np.float64)
    point = float(arr.mean())
    lower_q = (1.0 - ci_level) / 2.0 * 100.0
    upper_q = 100.0 - lower_q
    low = float(np.percentile(arr, lower_q))
    high = float(np.percentile(arr, upper_q))
    return point, low, high


__all__ = [
    "BootstrapResult",
    "bootstrap_fit",
    "market_ci_from_samples",
]
