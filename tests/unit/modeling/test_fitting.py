"""Tests for the Dixon-Coles fitter (L-BFGS)."""

import math
import random
from datetime import UTC, datetime

import pytest

from analytis.modeling.dixon_coles import score_matrix
from analytis.modeling.fitting import (
    DixonColesParams,
    FitConfig,
    MatchObservation,
    fit_dixon_coles,
)


def _synthetic_matches(
    n_teams: int = 6,
    n_rounds: int = 12,
    seed: int = 42,
) -> tuple[list[MatchObservation], DixonColesParams]:
    rng = random.Random(seed)
    teams = [f"T{i}" for i in range(n_teams)]
    # ground-truth params: attacks and defenses sum to zero
    attack = {t: rng.uniform(-0.4, 0.4) for t in teams}
    defense = {t: rng.uniform(-0.4, 0.4) for t in teams}
    # centre them
    a_mean = sum(attack.values()) / n_teams
    d_mean = sum(defense.values()) / n_teams
    attack = {t: a - a_mean for t, a in attack.items()}
    defense = {t: d - d_mean for t, d in defense.items()}
    truth = DixonColesParams(
        attack=attack,
        defense=defense,
        home_advantage=0.25,
        rho=-0.05,
    )

    matches: list[MatchObservation] = []
    day = 0
    for _ in range(n_rounds):
        for i in range(n_teams):
            for j in range(n_teams):
                if i == j:
                    continue
                home, away = teams[i], teams[j]
                lam_h = math.exp(truth.attack[home] - truth.defense[away] + truth.home_advantage)
                lam_a = math.exp(truth.attack[away] - truth.defense[home])
                hg = _poisson_sample(rng, lam_h)
                ag = _poisson_sample(rng, lam_a)
                matches.append(
                    MatchObservation(
                        home_team=home,
                        away_team=away,
                        home_goals=hg,
                        away_goals=ag,
                        kickoff_utc=datetime(2024, 1, 1, tzinfo=UTC).replace(day=1 + (day % 28)),
                        is_neutral=False,
                    )
                )
                day += 1
    return matches, truth


def _poisson_sample(rng: random.Random, lam: float) -> int:
    # Knuth's algorithm; fine for small lambdas in tests.
    L = math.exp(-lam)  # noqa: N806
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


def test_fitter_recovers_synthetic_params() -> None:
    matches, truth = _synthetic_matches(n_teams=6, n_rounds=20)
    cfg = FitConfig(max_iter=200, decay_per_day=0.0)
    fit = fit_dixon_coles(matches, config=cfg)
    # Home advantage and rho should be in the ballpark
    assert abs(fit.home_advantage - truth.home_advantage) < 0.15
    assert abs(fit.rho - truth.rho) < 0.15
    # Attack/defense diffs should be consistent
    attack_diff = max(fit.attack.values()) - min(fit.attack.values())
    truth_attack_diff = max(truth.attack.values()) - min(truth.attack.values())
    assert attack_diff == pytest.approx(truth_attack_diff, abs=0.3)


def test_fitter_returns_params_for_every_team() -> None:
    matches, _ = _synthetic_matches(n_teams=5, n_rounds=10)
    fit = fit_dixon_coles(matches)
    teams = {m.home_team for m in matches} | {m.away_team for m in matches}
    assert set(fit.attack.keys()) == teams
    assert set(fit.defense.keys()) == teams


def test_fitter_empty_matches_raises() -> None:
    with pytest.raises(ValueError, match="at least one match"):
        fit_dixon_coles([])


def test_fitter_produces_normalised_score_matrix() -> None:
    matches, _ = _synthetic_matches(n_teams=4, n_rounds=6)
    fit = fit_dixon_coles(matches)
    home, away = matches[0].home_team, matches[0].away_team
    lam_h = math.exp(fit.attack[home] - fit.defense[away] + fit.home_advantage)
    lam_a = math.exp(fit.attack[away] - fit.defense[home])
    M = score_matrix(lam_h, lam_a, fit.rho, max_goals=10)  # noqa: N806
    assert float(M.sum()) == pytest.approx(1.0, abs=1e-3)


def test_time_decay_weights_recent_more() -> None:
    matches, _ = _synthetic_matches(n_teams=4, n_rounds=10)
    fit_no_decay = fit_dixon_coles(matches, config=FitConfig(decay_per_day=0.0))
    fit_with_decay = fit_dixon_coles(matches, config=FitConfig(decay_per_day=0.01))
    # The two fits should differ — recent matches dominate the weighted one.
    diff = sum(abs(fit_no_decay.attack[t] - fit_with_decay.attack[t]) for t in fit_no_decay.attack)
    assert diff > 1e-3
