"""Team strength features — attack/defense per 90 with Bayesian shrinkage.

Each function is pure: given (history, prior) it returns a single float.
History is collected upstream (in the feature builder / use case).
Shrinkage is a simple "k virtual games at prior mean" — equivalent to
a conjugate update with a Gamma-Poisson rate prior:

    rate_shrunk = (sum_goals + prior_rate * k) / (total_minutes / 90 + k)

When `prior_strength` is 0, the function returns the raw observed rate.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchSample:
    goals_for: int
    goals_against: int
    minutes_played: int  # usually 90; can be lower for abandoned games


@dataclass(frozen=True)
class StrengthPrior:
    attack_per_90: float
    defense_per_90: float
    prior_strength: float  # "k" — number of virtual games at the prior mean


def _shrunk_rate(
    observed_goals: int,
    total_minutes: int,
    prior_rate: float,
    prior_strength: float,
) -> float:
    games_equivalent = total_minutes / 90.0
    denom = games_equivalent + prior_strength
    if denom <= 0:
        return prior_rate
    return (observed_goals + prior_rate * prior_strength) / denom


def shrunk_attack_per_90(*, history: list[MatchSample], prior: StrengthPrior) -> float:
    total_minutes = sum(m.minutes_played for m in history)
    total_goals_for = sum(m.goals_for for m in history)
    if total_minutes == 0:
        return prior.attack_per_90
    return _shrunk_rate(
        observed_goals=total_goals_for,
        total_minutes=total_minutes,
        prior_rate=prior.attack_per_90,
        prior_strength=prior.prior_strength,
    )


def shrunk_defense_per_90(*, history: list[MatchSample], prior: StrengthPrior) -> float:
    total_minutes = sum(m.minutes_played for m in history)
    total_goals_against = sum(m.goals_against for m in history)
    if total_minutes == 0:
        return prior.defense_per_90
    return _shrunk_rate(
        observed_goals=total_goals_against,
        total_minutes=total_minutes,
        prior_rate=prior.defense_per_90,
        prior_strength=prior.prior_strength,
    )


__all__ = [
    "MatchSample",
    "StrengthPrior",
    "shrunk_attack_per_90",
    "shrunk_defense_per_90",
]
