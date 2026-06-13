"""Tests for isotonic calibration."""

from itertools import pairwise

import numpy as np
import pytest

from analytis.modeling.isotonic import IsotonicCalibrator


def test_calibrator_fit_transform_identity() -> None:
    cal = IsotonicCalibrator()
    probs = [0.1, 0.3, 0.5, 0.7, 0.9]
    outcomes = [0, 0, 1, 1, 1]
    cal.fit(probs=probs, outcomes=outcomes)
    calibrated = [cal.predict(p) for p in probs]
    for a, b in pairwise(calibrated):
        assert a <= b


def test_calibrator_corrects_overconfidence() -> None:
    rng = np.random.default_rng(42)
    n = 500
    raw = rng.uniform(0, 1, size=n)
    true_prob = 0.5 * raw
    outcomes = (rng.uniform(0, 1, size=n) < true_prob).astype(int).tolist()

    cal = IsotonicCalibrator()
    cal.fit(probs=raw.tolist(), outcomes=outcomes)
    sample = 0.8
    out = cal.predict(sample)
    assert out < sample
    assert 0.0 <= out <= 1.0


def test_calibrator_predict_without_fit_raises() -> None:
    cal = IsotonicCalibrator()
    with pytest.raises(RuntimeError, match="not fitted"):
        cal.predict(0.5)
