import math

import pytest

from analytis.application.accuracy_summary import (
    normalize_phase,
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
