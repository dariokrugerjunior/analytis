"""Tests for World Football Elo math primitives."""

import pytest

from analytis.features.elo import (
    DEFAULT_RATING,
    expected_score,
    k_factor,
    update_ratings,
)


def test_expected_score_equal_strength() -> None:
    assert expected_score(1500.0, 1500.0) == pytest.approx(0.5, abs=1e-9)


def test_expected_score_stronger_home() -> None:
    es = expected_score(1700.0, 1500.0)
    assert 0.5 < es < 1.0
    assert es == pytest.approx(0.7597, abs=1e-3)


def test_expected_score_with_home_advantage() -> None:
    es_neutral = expected_score(1500.0, 1500.0, home_advantage=0.0)
    es_home = expected_score(1500.0, 1500.0, home_advantage=100.0)
    assert es_home > es_neutral


def test_k_factor_world_cup_higher_than_friendly() -> None:
    assert k_factor("FIFA World Cup") > k_factor("Friendly")


def test_k_factor_unknown_falls_back() -> None:
    assert k_factor("Some Obscure Tournament") == k_factor("Friendly")


def test_update_ratings_winner_gains_loser_loses() -> None:
    new_home, new_away = update_ratings(
        home_rating=1500.0,
        away_rating=1500.0,
        home_goals=2,
        away_goals=0,
        tournament="FIFA World Cup",
        is_neutral=True,
    )
    assert new_home > 1500.0
    assert new_away < 1500.0
    assert new_home + new_away == pytest.approx(3000.0, abs=1e-9)


def test_update_ratings_draw_zero_sum_around_expected() -> None:
    new_home, new_away = update_ratings(
        home_rating=1500.0,
        away_rating=1500.0,
        home_goals=1,
        away_goals=1,
        tournament="FIFA World Cup",
        is_neutral=True,
    )
    assert new_home == pytest.approx(1500.0, abs=1e-6)
    assert new_away == pytest.approx(1500.0, abs=1e-6)


def test_blowout_more_points_than_narrow_win() -> None:
    h_narrow, _ = update_ratings(
        1500.0,
        1500.0,
        1,
        0,
        tournament="FIFA World Cup",
        is_neutral=True,
    )
    h_blowout, _ = update_ratings(
        1500.0,
        1500.0,
        5,
        0,
        tournament="FIFA World Cup",
        is_neutral=True,
    )
    assert h_blowout > h_narrow


def test_default_rating_is_1500() -> None:
    assert DEFAULT_RATING == 1500.0
