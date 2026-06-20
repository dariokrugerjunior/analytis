import math

import pytest

from analytis.application.accuracy_summary import (
    actual_1x2,
    actual_btts,
    actual_ou,
    brier_binary,
    brier_multiclass,
    normalize_phase,
    predicted_1x2_top,
    wilson_ci,
)


@pytest.mark.parametrize(
    ("competition_round", "expected"),
    [
        ("GROUP_STAGE", "group"),
        ("LAST_16", "round_of_16"),
        ("QUARTER_FINALS", "quarterfinal"),
        ("SEMI_FINALS", "semifinal"),
        ("FINAL", "final"),
        ("THIRD_PLACE", "semifinal"),  # aggregated into semifinal
        ("unknown_value", "group"),  # fallback
        (None, "group"),  # null safe
    ],
)
def test_normalize_phase(competition_round: str | None, expected: str) -> None:
    assert normalize_phase(competition_round) == expected


def test_wilson_ci_known_case() -> None:
    # n=10, hits=7 → Wilson CI is approximately [0.397, 0.892]
    low, high = wilson_ci(hits=7, n=10)
    assert math.isclose(low, 0.3968, abs_tol=0.002)
    assert math.isclose(high, 0.8922, abs_tol=0.002)


def test_wilson_ci_n_zero_returns_full_range() -> None:
    low, high = wilson_ci(hits=0, n=0)
    assert low == 0.0
    assert high == 1.0


def test_wilson_ci_all_hits() -> None:
    low, high = wilson_ci(hits=5, n=5)
    assert low > 0.5
    assert high == pytest.approx(1.0, abs=1e-6)


def test_wilson_ci_no_hits() -> None:
    low, high = wilson_ci(hits=0, n=5)
    assert low == pytest.approx(0.0, abs=1e-6)
    assert high < 0.5


@pytest.mark.parametrize(
    ("home", "away", "expected"),
    [(2, 1, "home"), (1, 1, "draw"), (0, 3, "away"), (0, 0, "draw")],
)
def test_actual_1x2(home: int, away: int, expected: str) -> None:
    assert actual_1x2(home, away) == expected


@pytest.mark.parametrize(
    ("home", "away", "expected"),
    [(2, 1, "over"), (1, 1, "under"), (0, 2, "under"), (0, 3, "over")],
)
def test_actual_ou(home: int, away: int, expected: str) -> None:
    assert actual_ou(home, away) == expected


@pytest.mark.parametrize(
    ("home", "away", "expected"),
    [(2, 1, "yes"), (0, 1, "no"), (1, 0, "no"), (0, 0, "no")],
)
def test_actual_btts(home: int, away: int, expected: str) -> None:
    assert actual_btts(home, away) == expected


def test_predicted_1x2_top_picks_highest_prob() -> None:
    probs = {"home": 0.55, "draw": 0.25, "away": 0.20}
    assert predicted_1x2_top(probs) == ("home", 0.55)


def test_predicted_1x2_top_breaks_tie_alphabetically() -> None:
    # Deterministic tie-break: alphabetical earlier outcome wins on a tie.
    # 'draw' (d) comes before 'home' (h), so draw wins.
    probs = {"home": 0.40, "draw": 0.40, "away": 0.20}
    assert predicted_1x2_top(probs) == ("draw", 0.40)


def test_brier_binary_perfect_correct() -> None:
    # prob=1.0, outcome=1 → brier=0
    assert brier_binary(prob=1.0, outcome=1) == pytest.approx(0.0)


def test_brier_binary_perfect_wrong() -> None:
    # prob=1.0, outcome=0 → brier=1.0
    assert brier_binary(prob=1.0, outcome=0) == pytest.approx(1.0)


def test_brier_binary_coin_flip() -> None:
    # prob=0.5 always gives 0.25
    assert brier_binary(prob=0.5, outcome=1) == pytest.approx(0.25)
    assert brier_binary(prob=0.5, outcome=0) == pytest.approx(0.25)


def test_brier_multiclass_correct() -> None:
    # probs sum to 1, actual="home" → one-hot [1,0,0]
    # brier = ((p_home-1)^2 + p_draw^2 + p_away^2) / 3
    probs = {"home": 0.6, "draw": 0.3, "away": 0.1}
    expected = ((0.6 - 1.0) ** 2 + 0.3**2 + 0.1**2) / 3
    assert brier_multiclass(probs=probs, actual="home") == pytest.approx(expected)
