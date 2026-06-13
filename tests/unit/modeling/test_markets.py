"""Tests for market derivations from a Dixon-Coles score matrix."""

import numpy as np
import pytest

from analytis.modeling.dixon_coles import score_matrix
from analytis.modeling.markets import (
    btts_probabilities,
    match_result_probabilities,
    over_under_probabilities,
)


def _dc_matrix(lh: float = 1.4, la: float = 1.0, rho: float = -0.05) -> np.ndarray:
    return score_matrix(lh, la, rho, max_goals=10)


def test_match_result_sums_to_one() -> None:
    m = _dc_matrix()
    p = match_result_probabilities(m)
    assert p.home + p.draw + p.away == pytest.approx(1.0, abs=1e-3)
    assert 0.0 <= p.home <= 1.0
    assert 0.0 <= p.draw <= 1.0
    assert 0.0 <= p.away <= 1.0


def test_match_result_stronger_home_wins_more() -> None:
    weak_home = match_result_probabilities(_dc_matrix(lh=0.8, la=1.5))
    strong_home = match_result_probabilities(_dc_matrix(lh=2.0, la=0.6))
    assert strong_home.home > weak_home.home


def test_over_under_sums_to_one() -> None:
    m = _dc_matrix()
    p = over_under_probabilities(m, line=2.5)
    assert p.over + p.under == pytest.approx(1.0, abs=1e-3)


def test_over_under_higher_lambdas_more_over() -> None:
    low = over_under_probabilities(_dc_matrix(lh=0.8, la=0.7), line=2.5)
    high = over_under_probabilities(_dc_matrix(lh=2.0, la=1.8), line=2.5)
    assert high.over > low.over


def test_over_under_line_must_be_half() -> None:
    m = _dc_matrix()
    with pytest.raises(ValueError, match="half-integer"):
        over_under_probabilities(m, line=2.0)


def test_btts_sums_to_one() -> None:
    m = _dc_matrix()
    p = btts_probabilities(m)
    assert p.yes + p.no == pytest.approx(1.0, abs=1e-3)


def test_btts_yes_with_two_strong_attacks() -> None:
    weak = btts_probabilities(_dc_matrix(lh=0.5, la=0.5))
    strong = btts_probabilities(_dc_matrix(lh=1.8, la=1.8))
    assert strong.yes > weak.yes


def test_invalid_matrix_shape_raises() -> None:
    with pytest.raises(ValueError, match="square"):
        match_result_probabilities(np.zeros((3, 4)))
