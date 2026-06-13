"""Tests for Dixon-Coles math primitives."""

import math

import numpy as np
import pytest

from analytis.modeling.dixon_coles import (
    log_likelihood_match,
    score_matrix,
    tau,
)


def test_tau_returns_1_outside_low_scores() -> None:
    lh, la, rho = 1.4, 1.1, -0.1
    assert tau(0, 2, lh, la, rho) == pytest.approx(1.0)
    assert tau(2, 0, lh, la, rho) == pytest.approx(1.0)
    assert tau(2, 2, lh, la, rho) == pytest.approx(1.0)
    assert tau(3, 4, lh, la, rho) == pytest.approx(1.0)


def test_tau_low_scores() -> None:
    lh, la, rho = 1.0, 1.0, -0.1
    assert tau(0, 0, lh, la, rho) == pytest.approx(1.0 - lh * la * rho)
    assert tau(0, 1, lh, la, rho) == pytest.approx(1.0 + lh * rho)
    assert tau(1, 0, lh, la, rho) == pytest.approx(1.0 + la * rho)
    assert tau(1, 1, lh, la, rho) == pytest.approx(1.0 - rho)


def test_tau_rho_zero_is_neutral() -> None:
    for i in range(3):
        for j in range(3):
            assert tau(i, j, 1.4, 1.2, 0.0) == pytest.approx(1.0)


def test_score_matrix_sums_to_one() -> None:
    matrix = score_matrix(lambda_home=1.4, lambda_away=1.2, rho=-0.1, max_goals=10)
    assert matrix.shape == (11, 11)
    total = float(np.sum(matrix))
    assert total == pytest.approx(1.0, abs=1e-3)


def test_score_matrix_rho_zero_matches_independent_poisson() -> None:
    matrix = score_matrix(lambda_home=1.0, lambda_away=1.0, rho=0.0, max_goals=8)
    # Independent Poisson: P(i, j) = e^-1 * 1/i! * e^-1 * 1/j!
    expected_11 = math.exp(-1.0) * 1.0 * math.exp(-1.0) * 1.0
    assert float(matrix[1, 1]) == pytest.approx(expected_11, abs=1e-6)


def test_score_matrix_all_non_negative() -> None:
    matrix = score_matrix(lambda_home=1.4, lambda_away=1.0, rho=-0.2, max_goals=6)
    assert float(matrix.min()) >= 0.0


def test_log_likelihood_match_basic() -> None:
    ll = log_likelihood_match(
        home_goals=2,
        away_goals=1,
        lambda_home=1.5,
        lambda_away=1.0,
        rho=-0.1,
    )
    # Independent Poisson sanity bound — DC correction is 1.0 outside low scores
    expected_indep = (
        -1.5
        + 2 * math.log(1.5)
        - math.log(math.factorial(2))
        - 1.0
        + 1 * math.log(1.0)
        - math.log(math.factorial(1))
    )
    assert ll == pytest.approx(expected_indep, abs=1e-9)


def test_log_likelihood_match_low_scores_apply_correction() -> None:
    rho = -0.2
    ll = log_likelihood_match(
        home_goals=0,
        away_goals=0,
        lambda_home=1.0,
        lambda_away=1.0,
        rho=rho,
    )
    base = -1.0 - 1.0  # log(e^-1) + log(e^-1) for 0-0 in independent Poisson
    correction = math.log(1.0 - 1.0 * 1.0 * rho)
    assert ll == pytest.approx(base + correction, abs=1e-9)


def test_log_likelihood_raises_on_invalid_lambda() -> None:
    with pytest.raises(ValueError, match="lambda must be positive"):
        log_likelihood_match(
            home_goals=1,
            away_goals=1,
            lambda_home=0.0,
            lambda_away=1.0,
            rho=0.0,
        )


def test_log_likelihood_raises_on_invalid_correction() -> None:
    # rho large enough to make tau(0,0) <= 0 => log undefined
    with pytest.raises(ValueError, match="correction"):
        log_likelihood_match(
            home_goals=0,
            away_goals=0,
            lambda_home=1.0,
            lambda_away=1.0,
            rho=2.0,
        )
