"""Tests for EloRating domain entity."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from analytis.domain.elo import EloRating


def test_elo_rating_minimal() -> None:
    r = EloRating(
        team_id=uuid4(),
        rating=1500.0,
        as_of=datetime(2026, 6, 12, tzinfo=UTC),
    )
    assert r.rating == 1500.0


def test_elo_rating_rejects_naive() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        EloRating(team_id=uuid4(), rating=1500.0, as_of=datetime(2026, 6, 12))


def test_elo_rating_rejects_negative() -> None:
    with pytest.raises(ValueError, match="greater than or equal to 0"):
        EloRating(
            team_id=uuid4(),
            rating=-100.0,
            as_of=datetime(2026, 6, 12, tzinfo=UTC),
        )
