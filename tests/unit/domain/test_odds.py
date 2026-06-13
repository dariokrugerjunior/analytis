"""Tests for OddsQuote domain entity."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from analytis.domain.odds import BookmakerKey, OddsQuote


def test_odds_quote_minimal() -> None:
    q = OddsQuote(
        match_id=uuid4(),
        bookmaker=BookmakerKey("pinnacle"),
        market="1x2",
        outcome="home",
        decimal_odds=2.10,
        snapshot_taken_at=datetime(2026, 6, 13, tzinfo=UTC),
    )
    assert q.decimal_odds == 2.10
    assert q.implied_probability() == pytest.approx(1.0 / 2.10, abs=1e-9)


def test_odds_quote_rejects_decimal_below_one() -> None:
    with pytest.raises(ValueError, match="decimal_odds"):
        OddsQuote(
            match_id=uuid4(),
            bookmaker=BookmakerKey("any"),
            market="1x2",
            outcome="home",
            decimal_odds=0.99,
            snapshot_taken_at=datetime(2026, 6, 13, tzinfo=UTC),
        )


def test_odds_quote_naive_snapshot_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        OddsQuote(
            match_id=uuid4(),
            bookmaker=BookmakerKey("any"),
            market="1x2",
            outcome="home",
            decimal_odds=2.0,
            snapshot_taken_at=datetime(2026, 6, 13),
        )


def test_bookmaker_key_normalises() -> None:
    assert BookmakerKey("  PinNacle  ") == "pinnacle"
    assert BookmakerKey("BET 365") == "bet_365"


def test_bookmaker_key_rejects_empty() -> None:
    with pytest.raises(ValueError, match="bookmaker key"):
        BookmakerKey("")
