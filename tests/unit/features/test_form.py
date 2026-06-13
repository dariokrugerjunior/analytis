"""Tests for recent-form features (rolling window + exponential decay)."""

import math

import pytest

from analytis.features.form import (
    FormSample,
    form_goal_diff,
    form_goals_against,
    form_goals_for,
)

_DECAY = 0.3


def test_empty_history_returns_none() -> None:
    assert form_goals_for(history=[], decay=_DECAY) is None
    assert form_goals_against(history=[], decay=_DECAY) is None
    assert form_goal_diff(history=[], decay=_DECAY) is None


def test_single_match_returns_observed_values() -> None:
    h = [FormSample(goals_for=2, goals_against=1)]
    assert form_goals_for(history=h, decay=_DECAY) == pytest.approx(2.0)
    assert form_goals_against(history=h, decay=_DECAY) == pytest.approx(1.0)
    assert form_goal_diff(history=h, decay=_DECAY) == pytest.approx(1.0)


def test_decay_weights_recent_more() -> None:
    # Two games: most recent = 3 goals, older = 1 goal.
    # With decay=0.3, weights are 1.0 and exp(-0.3) ≈ 0.7408.
    h = [
        FormSample(goals_for=3, goals_against=0),  # most recent
        FormSample(goals_for=1, goals_against=0),  # older
    ]
    w0, w1 = 1.0, math.exp(-_DECAY)
    expected = (3.0 * w0 + 1.0 * w1) / (w0 + w1)
    assert form_goals_for(history=h, decay=_DECAY) == pytest.approx(expected, abs=1e-9)


def test_decay_zero_equals_simple_average() -> None:
    h = [
        FormSample(goals_for=3, goals_against=0),
        FormSample(goals_for=1, goals_against=0),
    ]
    assert form_goals_for(history=h, decay=0.0) == pytest.approx(2.0)


def test_decay_large_collapses_to_latest() -> None:
    h = [
        FormSample(goals_for=3, goals_against=1),
        FormSample(goals_for=99, goals_against=99),  # ancient game
    ]
    # With decay=20, the older sample's weight is negligible.
    assert form_goals_for(history=h, decay=20.0) == pytest.approx(3.0, abs=1e-3)


def test_window_limits_history() -> None:
    h = [FormSample(goals_for=2, goals_against=0) for _ in range(20)]
    # window=5 means only the 5 most recent matter
    fg5 = form_goals_for(history=h, decay=_DECAY, window=5)
    fg_all = form_goals_for(history=h, decay=_DECAY)
    assert fg5 == pytest.approx(2.0)
    assert fg_all == pytest.approx(2.0)


def test_invalid_decay_raises() -> None:
    h = [FormSample(goals_for=1, goals_against=0)]
    with pytest.raises(ValueError, match="decay must be non-negative"):
        form_goals_for(history=h, decay=-0.1)


def test_invalid_window_raises() -> None:
    h = [FormSample(goals_for=1, goals_against=0)]
    with pytest.raises(ValueError, match="window must be positive"):
        form_goals_for(history=h, decay=_DECAY, window=0)
