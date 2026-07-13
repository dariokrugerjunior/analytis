"""Unit tests for the dashboard per-game scoring logic."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from analytis.application.accuracy_summary import MatchRow
from analytis.application.dashboard_scores import (
    build_aggregate,
    build_games,
    match_points,
)

# ---- match_points: the core scoring rule (all branches) ----


@pytest.mark.parametrize(
    ("pred", "actual", "expected"),
    [
        # exact score -> 100
        ((2, 1), (2, 1), 100),
        # exact draw -> 100 (covered by the exact-score branch)
        ((1, 1), (1, 1), 100),
        ((0, 0), (0, 0), 100),
        # correct winner, wrong score -> 50
        ((2, 0), (3, 1), 50),  # both home wins
        ((0, 2), (1, 3), 50),  # both away wins
        # correct draw, wrong score -> 50
        ((1, 1), (2, 2), 50),
        ((0, 0), (1, 1), 50),
        # wrong outcome -> 0
        ((2, 1), (0, 2), 0),  # predicted home win, was away win
        ((1, 1), (2, 0), 0),  # predicted draw, was home win
        ((0, 1), (1, 1), 0),  # predicted away win, was draw
    ],
)
def test_match_points_all_branches(
    pred: tuple[int, int], actual: tuple[int, int], expected: int
) -> None:
    assert match_points(pred[0], pred[1], actual[0], actual[1]) == expected


def test_exact_draw_scores_100_not_50() -> None:
    # An exactly-correct draw must resolve via the exact-score branch (100),
    # never the outcome branch (50).
    assert match_points(2, 2, 2, 2) == 100


# ---- build_games / build_aggregate ----


def _row(
    *,
    kickoff: datetime,
    home_goals: int,
    away_goals: int,
    pred_home: int | None,
    pred_away: int | None,
    home_team: str = "H",
    away_team: str = "A",
) -> MatchRow:
    return MatchRow(
        match_id=uuid4(),
        kickoff_utc=kickoff,
        home_team=home_team,
        away_team=away_team,
        home_goals=home_goals,
        away_goals=away_goals,
        phase="group",
        predictions={},
        scoreline_credit=None,
        scoreline_predicted_home=pred_home,
        scoreline_predicted_away=pred_away,
    )


def test_build_games_skips_rows_without_scoreline() -> None:
    rows = [
        _row(
            kickoff=datetime(2026, 6, 14, tzinfo=UTC),
            home_goals=2,
            away_goals=1,
            pred_home=None,
            pred_away=None,
        ),
        _row(
            kickoff=datetime(2026, 6, 15, tzinfo=UTC),
            home_goals=2,
            away_goals=1,
            pred_home=2,
            pred_away=1,
        ),
    ]
    games = build_games(rows)
    assert len(games) == 1
    g = games[0]
    assert g.points == 100
    assert g.predicted_score == "2-1"
    assert g.actual_score == "2-1"
    assert g.outcome_predicted == "home"
    assert g.outcome_actual == "home"


def test_build_games_is_chronological() -> None:
    rows = [
        _row(
            kickoff=datetime(2026, 6, 20, tzinfo=UTC),
            home_goals=1,
            away_goals=0,
            pred_home=1,
            pred_away=0,
            home_team="Late",
        ),
        _row(
            kickoff=datetime(2026, 6, 14, tzinfo=UTC),
            home_goals=1,
            away_goals=0,
            pred_home=1,
            pred_away=0,
            home_team="Early",
        ),
    ]
    games = build_games(rows)
    assert [g.home_team for g in games] == ["Early", "Late"]


def test_build_aggregate_counts_and_average() -> None:
    rows = [
        # exact -> 100
        _row(
            kickoff=datetime(2026, 6, 14, tzinfo=UTC),
            home_goals=2,
            away_goals=1,
            pred_home=2,
            pred_away=1,
        ),
        # correct outcome, wrong score -> 50
        _row(
            kickoff=datetime(2026, 6, 15, tzinfo=UTC),
            home_goals=3,
            away_goals=1,
            pred_home=2,
            pred_away=0,
        ),
        # wrong outcome -> 0
        _row(
            kickoff=datetime(2026, 6, 16, tzinfo=UTC),
            home_goals=0,
            away_goals=2,
            pred_home=2,
            pred_away=1,
        ),
    ]
    agg = build_aggregate(build_games(rows))
    assert agg.total_games == 3
    assert agg.exact == 1
    assert agg.outcome_only == 1
    assert agg.missed == 1
    assert agg.avg_points == pytest.approx((100 + 50 + 0) / 3)


def test_build_aggregate_empty() -> None:
    agg = build_aggregate([])
    assert agg.total_games == 0
    assert agg.avg_points == 0.0
    assert agg.exact == agg.outcome_only == agg.missed == 0
