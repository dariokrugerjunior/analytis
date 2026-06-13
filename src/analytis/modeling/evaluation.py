"""Evaluation metrics for probabilistic binary predictions.

- Brier score: mean squared difference between predicted prob and outcome (lower is better).
- Log-loss: mean negative log probability of the realized outcome.
- Expected Calibration Error (ECE): weighted mean absolute gap between
  predicted prob and observed frequency, per bin.
- Reliability diagram: per-bin (mean_predicted, mean_observed, count).
"""

import math
from dataclasses import dataclass

_EPS = 1e-12


@dataclass(frozen=True)
class ReliabilityBin:
    lower: float
    upper: float
    count: int
    mean_predicted: float
    observed_frequency: float


def _validate(probs: list[float], outcomes: list[int]) -> None:
    if len(probs) != len(outcomes):
        raise ValueError("probs and outcomes must have the same length")
    for p in probs:
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"prob out of range: {p}")
    for o in outcomes:
        if o not in (0, 1):
            raise ValueError(f"outcome must be 0 or 1, got {o}")


def brier_score(*, probs: list[float], outcomes: list[int]) -> float:
    _validate(probs, outcomes)
    if not probs:
        return 0.0
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes, strict=True)) / len(probs)


def log_loss(*, probs: list[float], outcomes: list[int]) -> float:
    _validate(probs, outcomes)
    if not probs:
        return 0.0
    total = 0.0
    for p, o in zip(probs, outcomes, strict=True):
        p_clipped = min(max(p, _EPS), 1.0 - _EPS)
        total += -(o * math.log(p_clipped) + (1 - o) * math.log(1 - p_clipped))
    return total / len(probs)


def reliability_diagram(
    *, probs: list[float], outcomes: list[int], n_bins: int = 10
) -> list[ReliabilityBin]:
    _validate(probs, outcomes)
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")
    bins: list[ReliabilityBin] = []
    edges = [i / n_bins for i in range(n_bins + 1)]
    for k in range(n_bins):
        lo, hi = edges[k], edges[k + 1]
        bucketed = [
            (p, o)
            for p, o in zip(probs, outcomes, strict=True)
            if (p >= lo and (p < hi or (k == n_bins - 1 and p <= hi)))
        ]
        count = len(bucketed)
        if count == 0:
            bins.append(
                ReliabilityBin(
                    lower=lo,
                    upper=hi,
                    count=0,
                    mean_predicted=0.0,
                    observed_frequency=0.0,
                )
            )
            continue
        mean_p = sum(p for p, _ in bucketed) / count
        freq = sum(o for _, o in bucketed) / count
        bins.append(
            ReliabilityBin(
                lower=lo,
                upper=hi,
                count=count,
                mean_predicted=mean_p,
                observed_frequency=freq,
            )
        )
    return bins


def expected_calibration_error(
    *, probs: list[float], outcomes: list[int], n_bins: int = 10
) -> float:
    bins = reliability_diagram(probs=probs, outcomes=outcomes, n_bins=n_bins)
    total = len(probs)
    if total == 0:
        return 0.0
    weighted = 0.0
    for b in bins:
        if b.count == 0:
            continue
        weighted += (b.count / total) * abs(b.mean_predicted - b.observed_frequency)
    return weighted


__all__ = [
    "ReliabilityBin",
    "brier_score",
    "expected_calibration_error",
    "log_loss",
    "reliability_diagram",
]
