"""Tests for evaluation metrics: Brier score, log-loss, ECE."""

import pytest

from analytis.modeling.evaluation import (
    brier_score,
    expected_calibration_error,
    log_loss,
    reliability_diagram,
)


def test_brier_perfect_predictions() -> None:
    probs = [1.0, 0.0, 1.0, 0.0]
    outcomes = [1, 0, 1, 0]
    assert brier_score(probs=probs, outcomes=outcomes) == pytest.approx(0.0)


def test_brier_worst_predictions() -> None:
    probs = [0.0, 1.0, 0.0, 1.0]
    outcomes = [1, 0, 1, 0]
    assert brier_score(probs=probs, outcomes=outcomes) == pytest.approx(1.0)


def test_brier_calibrated_random() -> None:
    # 50/50 predictions on random outcomes — Brier = 0.25.
    probs = [0.5] * 100
    outcomes = [0, 1] * 50
    assert brier_score(probs=probs, outcomes=outcomes) == pytest.approx(0.25)


def test_log_loss_perfect_predictions() -> None:
    probs = [1.0, 0.0, 1.0, 0.0]
    outcomes = [1, 0, 1, 0]
    # Some implementations clip to eps to avoid log(0); we expect a small positive.
    assert log_loss(probs=probs, outcomes=outcomes) < 1e-6


def test_log_loss_penalises_wrong_confident() -> None:
    almost_right = log_loss(probs=[0.9, 0.1], outcomes=[1, 0])
    almost_wrong = log_loss(probs=[0.1, 0.9], outcomes=[1, 0])
    assert almost_wrong > almost_right


def test_log_loss_mismatched_lengths_raises() -> None:
    with pytest.raises(ValueError, match="length"):
        log_loss(probs=[0.5, 0.5], outcomes=[1])


def test_ece_perfectly_calibrated() -> None:
    # 20 predictions at 0.7 — 14 outcomes positive.
    probs = [0.7] * 20
    outcomes = [1] * 14 + [0] * 6
    assert expected_calibration_error(probs=probs, outcomes=outcomes, n_bins=10) == pytest.approx(
        0.0, abs=1e-9
    )


def test_ece_overconfident() -> None:
    # 10 predictions at 0.9, all wrong — bin freq = 0, predicted = 0.9, gap = 0.9.
    probs = [0.9] * 10
    outcomes = [0] * 10
    ece = expected_calibration_error(probs=probs, outcomes=outcomes, n_bins=10)
    assert ece == pytest.approx(0.9, abs=1e-9)


def test_reliability_diagram_buckets() -> None:
    probs = [0.05, 0.15, 0.25, 0.35, 0.55, 0.65, 0.75, 0.85, 0.95]
    outcomes = [0, 0, 0, 1, 1, 1, 1, 1, 1]
    bins = reliability_diagram(probs=probs, outcomes=outcomes, n_bins=10)
    assert len(bins) == 10
    # First bin (0.0-0.1) should contain one prediction (0.05).
    assert bins[0].count == 1
    # Bin 9 (0.9-1.0) should contain one prediction (0.95).
    assert bins[9].count == 1
