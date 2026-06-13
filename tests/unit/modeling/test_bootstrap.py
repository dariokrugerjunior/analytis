"""Tests for bootstrap CI of Dixon-Coles fits."""

import random
from datetime import UTC, datetime

import pytest

from analytis.modeling.bootstrap import (
    BootstrapResult,
    bootstrap_fit,
    market_ci_from_samples,
)
from analytis.modeling.fitting import MatchObservation


def _synth_matches(n_teams: int = 4, n_rounds: int = 8, seed: int = 1) -> list[MatchObservation]:
    rng = random.Random(seed)
    teams = [f"T{i}" for i in range(n_teams)]
    obs: list[MatchObservation] = []
    day = 0
    for _ in range(n_rounds):
        for i, h in enumerate(teams):
            for j, a in enumerate(teams):
                if i == j:
                    continue
                obs.append(
                    MatchObservation(
                        home_team=h,
                        away_team=a,
                        home_goals=rng.randint(0, 3),
                        away_goals=rng.randint(0, 3),
                        kickoff_utc=datetime(2024, 1, 1, tzinfo=UTC),
                        is_neutral=False,
                    )
                )
                day += 1
    return obs


def test_bootstrap_returns_n_samples() -> None:
    matches = _synth_matches()
    result = bootstrap_fit(matches, n_samples=5, max_iter=50, seed=42)
    assert isinstance(result, BootstrapResult)
    assert len(result.samples) == 5
    assert all("T0" in s.attack for s in result.samples)


def test_market_ci_from_samples_brackets_point_estimate() -> None:
    matches = _synth_matches()
    result = bootstrap_fit(matches, n_samples=20, max_iter=50, seed=1)
    home, away = "T0", "T1"
    point, low, high = market_ci_from_samples(
        result.samples,
        home_team=home,
        away_team=away,
        market="1x2",
        outcome="home",
        is_neutral=False,
    )
    assert 0.0 <= low <= point <= high <= 1.0
    assert high - low > 1e-3


def test_market_ci_known_team_missing_raises() -> None:
    matches = _synth_matches()
    result = bootstrap_fit(matches, n_samples=5, max_iter=50, seed=2)
    with pytest.raises(KeyError):
        market_ci_from_samples(
            result.samples,
            home_team="UNKNOWN",
            away_team="T0",
            market="1x2",
            outcome="home",
            is_neutral=False,
        )
