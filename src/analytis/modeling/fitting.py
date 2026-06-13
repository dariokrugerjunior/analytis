"""Dixon-Coles parameter fitting via L-BFGS over negative log-likelihood.

Parameterisation:
    For team i: attack_i (real), defense_i (real)
    home_advantage gamma (real)
    rho (real, in (-1, 1) practical bounds)

Per-match means:
    lambda_home = exp(attack_home - defense_away + gamma * is_home_not_neutral)
    lambda_away = exp(attack_away - defense_home)

Identifiability: we add a soft constraint that sum(attack) = sum(defense) = 0.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from analytis.modeling.confederation_prior import (
    ConfederationPrior,
    confederation_penalty,
)
from analytis.modeling.dixon_coles import log_likelihood_match


@dataclass(frozen=True)
class MatchObservation:
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    kickoff_utc: datetime
    is_neutral: bool


@dataclass(frozen=True)
class FitConfig:
    max_iter: int = 200
    decay_per_day: float = 0.0  # 0 => no decay
    identifiability_penalty: float = 1.0
    initial_home_advantage: float = 0.3
    initial_rho: float = -0.05
    confederation_prior: ConfederationPrior | None = None


@dataclass
class DixonColesParams:
    attack: dict[str, float] = field(default_factory=dict)
    defense: dict[str, float] = field(default_factory=dict)
    home_advantage: float = 0.0
    rho: float = 0.0


def _team_index(matches: list[MatchObservation]) -> list[str]:
    teams: set[str] = set()
    for m in matches:
        teams.add(m.home_team)
        teams.add(m.away_team)
    return sorted(teams)


def _weights(matches: list[MatchObservation], decay_per_day: float) -> NDArray[np.float64]:
    if decay_per_day <= 0:
        return np.ones(len(matches), dtype=np.float64)
    latest = max(m.kickoff_utc for m in matches)
    w = np.empty(len(matches), dtype=np.float64)
    for i, m in enumerate(matches):
        delta_days = (latest - m.kickoff_utc).days
        w[i] = math.exp(-decay_per_day * delta_days)
    return w


def _unpack(
    x: NDArray[np.float64], n_teams: int
) -> tuple[NDArray[np.float64], NDArray[np.float64], float, float]:
    attack = x[:n_teams]
    defense = x[n_teams : 2 * n_teams]
    home_advantage = float(x[2 * n_teams])
    rho = float(x[2 * n_teams + 1])
    return attack, defense, home_advantage, rho


def _neg_log_likelihood(
    x: NDArray[np.float64],
    matches: list[MatchObservation],
    team_to_idx: dict[str, int],
    weights: NDArray[np.float64],
    identifiability_penalty: float,
    confederation_prior: ConfederationPrior | None,
) -> float:
    n_teams = len(team_to_idx)
    attack, defense, gamma, rho = _unpack(x, n_teams)
    total = 0.0
    for i, m in enumerate(matches):
        h_idx = team_to_idx[m.home_team]
        a_idx = team_to_idx[m.away_team]
        ha = 0.0 if m.is_neutral else gamma
        lam_h = math.exp(attack[h_idx] - defense[a_idx] + ha)
        lam_a = math.exp(attack[a_idx] - defense[h_idx])
        try:
            ll = log_likelihood_match(
                home_goals=m.home_goals,
                away_goals=m.away_goals,
                lambda_home=lam_h,
                lambda_away=lam_a,
                rho=rho,
            )
        except ValueError:
            return 1e9
        total += float(weights[i]) * ll
    penalty = identifiability_penalty * (float(np.mean(attack)) ** 2 + float(np.mean(defense)) ** 2)
    extra_penalty = 0.0
    if confederation_prior is not None and confederation_prior.is_active():
        attack_dict = {t: float(attack[i]) for t, i in team_to_idx.items()}
        defense_dict = {t: float(defense[i]) for t, i in team_to_idx.items()}
        extra_penalty = confederation_penalty(
            attack=attack_dict,
            defense=defense_dict,
            prior=confederation_prior,
        )
    return -total + penalty * len(matches) + extra_penalty


def fit_dixon_coles(
    matches: list[MatchObservation],
    config: FitConfig | None = None,
) -> DixonColesParams:
    if not matches:
        raise ValueError("fit_dixon_coles requires at least one match")
    cfg = config or FitConfig()
    teams = _team_index(matches)
    n = len(teams)
    team_to_idx = {t: i for i, t in enumerate(teams)}
    weights = _weights(matches, cfg.decay_per_day)

    x0 = np.zeros(2 * n + 2, dtype=np.float64)
    x0[2 * n] = cfg.initial_home_advantage
    x0[2 * n + 1] = cfg.initial_rho

    bounds: list[tuple[float | None, float | None]] = [(-3.0, 3.0)] * (2 * n)
    bounds.append((-1.0, 2.0))  # home_advantage
    bounds.append((-0.5, 0.5))  # rho

    result = minimize(
        _neg_log_likelihood,
        x0,
        args=(
            matches,
            team_to_idx,
            weights,
            cfg.identifiability_penalty,
            cfg.confederation_prior,
        ),
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": cfg.max_iter},
    )

    attack_vec, defense_vec, gamma, rho = _unpack(result.x, n)
    return DixonColesParams(
        attack={t: float(attack_vec[i]) for t, i in team_to_idx.items()},
        defense={t: float(defense_vec[i]) for t, i in team_to_idx.items()},
        home_advantage=gamma,
        rho=rho,
    )


__all__ = [
    "DixonColesParams",
    "FitConfig",
    "MatchObservation",
    "fit_dixon_coles",
]
