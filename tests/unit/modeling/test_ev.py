"""Tests for EV math."""

import pytest

from analytis.modeling.ev import edge, implied_probability, remove_overround


def test_implied_probability() -> None:
    assert implied_probability(2.0) == pytest.approx(0.5)
    assert implied_probability(1.50) == pytest.approx(0.6667, abs=1e-3)


def test_edge_positive_when_model_beats_market() -> None:
    e = edge(our_prob=0.55, decimal_odds=2.10)
    assert e > 0
    expected = 0.55 * 1.10 - 0.45
    assert e == pytest.approx(expected, abs=1e-9)


def test_edge_negative_when_market_beats_model() -> None:
    e = edge(our_prob=0.40, decimal_odds=2.10)
    assert e < 0


def test_remove_overround_h2h() -> None:
    fair = remove_overround([1.85, 3.50, 4.20])
    assert sum(fair) == pytest.approx(1.0, abs=1e-9)
    assert fair[0] > fair[1] > fair[2]


def test_remove_overround_two_way() -> None:
    fair = remove_overround([1.91, 1.91])
    assert sum(fair) == pytest.approx(1.0, abs=1e-9)
    assert fair[0] == pytest.approx(0.5)
