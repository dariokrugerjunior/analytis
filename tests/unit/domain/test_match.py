"""Tests for Match domain entity."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from analytis.domain.match import Match, MatchStatus


def test_match_minimal() -> None:
    m = Match(
        season_id=uuid4(),
        home_team_id=uuid4(),
        away_team_id=uuid4(),
        kickoff_utc=datetime(2026, 6, 15, 20, 0, tzinfo=UTC),
    )
    assert m.status is MatchStatus.SCHEDULED


def test_match_rejects_same_team() -> None:
    tid = uuid4()
    with pytest.raises(ValueError, match="cannot play itself"):
        Match(
            season_id=uuid4(),
            home_team_id=tid,
            away_team_id=tid,
            kickoff_utc=datetime(2026, 6, 15, 20, 0, tzinfo=UTC),
        )


def test_match_finished_requires_goals() -> None:
    m = Match(
        season_id=uuid4(),
        home_team_id=uuid4(),
        away_team_id=uuid4(),
        kickoff_utc=datetime(2026, 6, 15, 20, 0, tzinfo=UTC),
        status=MatchStatus.FINISHED,
        home_goals=2,
        away_goals=1,
    )
    assert m.home_goals == 2


def test_match_finished_rejects_missing_goals() -> None:
    with pytest.raises(ValueError, match="finished match requires goals"):
        Match(
            season_id=uuid4(),
            home_team_id=uuid4(),
            away_team_id=uuid4(),
            kickoff_utc=datetime(2026, 6, 15, 20, 0, tzinfo=UTC),
            status=MatchStatus.FINISHED,
        )


def test_match_naive_kickoff_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Match(
            season_id=uuid4(),
            home_team_id=uuid4(),
            away_team_id=uuid4(),
            kickoff_utc=datetime(2026, 6, 15, 20, 0),
        )
