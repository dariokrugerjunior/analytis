"""Tests for XGBoost goals regressor."""

import math
import random

import pytest

from analytis.modeling.xgboost_regressor import XGBoostGoalsRegressor


def _synth_dataset(
    n: int = 400, seed: int = 1
) -> tuple[list[dict[str, object]], list[tuple[int, int]]]:
    rng = random.Random(seed)
    features: list[dict[str, object]] = []
    outcomes: list[tuple[int, int]] = []
    for _ in range(n):
        elo_diff = rng.uniform(-300, 300)
        rest_diff = rng.uniform(-3, 3)
        # Higher elo_diff -> home tends to score more
        lam_h = math.exp(0.6 + elo_diff / 600.0)
        lam_a = math.exp(0.4 - elo_diff / 600.0)

        # Simple sampling (Knuth)
        def _samp(lam: float) -> int:
            threshold = math.exp(-lam)
            k = 0
            p = 1.0
            while True:
                k += 1
                p *= rng.random()
                if p <= threshold:
                    return k - 1

        features.append({"elo_diff": elo_diff, "rest_diff": rest_diff})
        outcomes.append((_samp(lam_h), _samp(lam_a)))
    return features, outcomes


def test_regressor_rejects_bad_side() -> None:
    with pytest.raises(ValueError, match="side must be"):
        XGBoostGoalsRegressor(side="middle")


def test_regressor_unfitted_raises() -> None:
    reg = XGBoostGoalsRegressor(side="home")
    with pytest.raises(RuntimeError, match="not fitted"):
        reg.predict_one({"elo_diff": 0.0})


def test_regressor_home_higher_for_strong_home_diff() -> None:
    features, outcomes = _synth_dataset(n=400)
    reg = XGBoostGoalsRegressor(side="home", n_estimators=100, max_depth=3)
    reg.fit(features, outcomes)

    strong_home = reg.predict_one({"elo_diff": 250.0, "rest_diff": 0.0})
    weak_home = reg.predict_one({"elo_diff": -250.0, "rest_diff": 0.0})
    assert strong_home > weak_home
    assert strong_home > 0.5
    assert weak_home > 0.0


def test_regressor_away_higher_for_strong_away_diff() -> None:
    features, outcomes = _synth_dataset(n=400)
    reg = XGBoostGoalsRegressor(side="away", n_estimators=100, max_depth=3)
    reg.fit(features, outcomes)

    strong_away = reg.predict_one({"elo_diff": -250.0, "rest_diff": 0.0})
    weak_away = reg.predict_one({"elo_diff": 250.0, "rest_diff": 0.0})
    assert strong_away > weak_away


def test_regressor_clamps_to_positive() -> None:
    features, outcomes = _synth_dataset(n=200)
    reg = XGBoostGoalsRegressor(side="home", n_estimators=50)
    reg.fit(features, outcomes)
    out = reg.predict_one({"elo_diff": -999.0, "rest_diff": -10.0})
    assert out >= 0.05
