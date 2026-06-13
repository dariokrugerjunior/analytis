"""Tests for context features (rest, neutral, stage, H2H)."""

from datetime import UTC, datetime

import pytest

from analytis.features.context import (
    H2HSample,
    h2h_home_win_rate,
    h2h_total_goals_avg,
    is_elimination_stage,
    rest_days,
)


def test_rest_days_simple() -> None:
    last = datetime(2026, 6, 10, 18, 0, tzinfo=UTC)
    now = datetime(2026, 6, 14, 18, 0, tzinfo=UTC)
    assert rest_days(last_match_at=last, current_match_at=now) == 4


def test_rest_days_same_day_is_zero() -> None:
    last = datetime(2026, 6, 14, 10, 0, tzinfo=UTC)
    now = datetime(2026, 6, 14, 18, 0, tzinfo=UTC)
    assert rest_days(last_match_at=last, current_match_at=now) == 0


def test_rest_days_none_history_is_none() -> None:
    now = datetime(2026, 6, 14, 18, 0, tzinfo=UTC)
    assert rest_days(last_match_at=None, current_match_at=now) is None


def test_rest_days_negative_raises() -> None:
    last = datetime(2026, 6, 15, 18, 0, tzinfo=UTC)
    now = datetime(2026, 6, 14, 18, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="last_match_at must be before"):
        rest_days(last_match_at=last, current_match_at=now)


def test_is_elimination_stage() -> None:
    assert is_elimination_stage("ROUND_OF_16") is True
    assert is_elimination_stage("QUARTER_FINALS") is True
    assert is_elimination_stage("SEMI_FINALS") is True
    assert is_elimination_stage("FINAL") is True
    assert is_elimination_stage("THIRD_PLACE") is True
    assert is_elimination_stage("GROUP_STAGE") is False
    assert is_elimination_stage("REGULAR_SEASON") is False
    assert is_elimination_stage(None) is False
    assert is_elimination_stage("") is False


def test_is_elimination_stage_case_insensitive() -> None:
    assert is_elimination_stage("final") is True
    assert is_elimination_stage("Round_of_16") is True


def test_h2h_home_win_rate_empty_history_is_none() -> None:
    assert h2h_home_win_rate(history=[]) is None


def test_h2h_home_win_rate_all_home_wins() -> None:
    h = [H2HSample(home_goals=2, away_goals=0)] * 5
    assert h2h_home_win_rate(history=h) == pytest.approx(1.0)


def test_h2h_home_win_rate_mixed() -> None:
    h = [
        H2HSample(home_goals=2, away_goals=0),  # home win
        H2HSample(home_goals=1, away_goals=1),  # draw
        H2HSample(home_goals=0, away_goals=2),  # away win
        H2HSample(home_goals=3, away_goals=1),  # home win
    ]
    # 2 home wins, 1 draw counts 0.5, 1 away win = (2 + 0.5) / 4 = 0.625
    assert h2h_home_win_rate(history=h) == pytest.approx(0.625)


def test_h2h_total_goals_avg_empty_is_none() -> None:
    assert h2h_total_goals_avg(history=[]) is None


def test_h2h_total_goals_avg_basic() -> None:
    h = [
        H2HSample(home_goals=2, away_goals=1),  # 3
        H2HSample(home_goals=0, away_goals=0),  # 0
        H2HSample(home_goals=1, away_goals=2),  # 3
    ]
    assert h2h_total_goals_avg(history=h) == pytest.approx(2.0)
