"""Tests for fractional Kelly stake."""

import pytest

from analytis.modeling.kelly import kelly_fraction, kelly_stake_units


def test_kelly_zero_edge_is_zero() -> None:
    assert kelly_fraction(our_prob=0.5, decimal_odds=2.0) == pytest.approx(0.0)


def test_kelly_positive_edge() -> None:
    f = kelly_fraction(our_prob=0.55, decimal_odds=2.0)
    # f = (b*p - q) / b where b = odds-1, p=0.55, q=0.45 -> f = (1*0.55 - 0.45)/1 = 0.10
    assert f == pytest.approx(0.10, abs=1e-9)


def test_kelly_negative_capped_at_zero() -> None:
    f = kelly_fraction(our_prob=0.40, decimal_odds=2.0)
    assert f == 0.0


def test_kelly_stake_units_fractional_kelly() -> None:
    units = kelly_stake_units(
        our_prob=0.55,
        decimal_odds=2.0,
        bankroll=1000.0,
        fraction=0.25,
    )
    # Full kelly = 100 (10% of 1000); 1/4 kelly = 25.
    assert units == pytest.approx(25.0, abs=1e-9)


def test_kelly_stake_units_caps_at_max() -> None:
    units = kelly_stake_units(
        our_prob=0.99,
        decimal_odds=2.0,
        bankroll=1000.0,
        fraction=1.0,
        max_units=20.0,
    )
    assert units == 20.0
