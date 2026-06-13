"""Odds quote domain entity."""

import re
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from analytis.domain.ids import MatchId


def BookmakerKey(value: str) -> str:  # noqa: N802 — factory, not a class
    """Normalise to lowercase, alnum, underscore-separated."""
    cleaned = value.strip().lower()
    if not cleaned:
        raise ValueError("bookmaker key cannot be empty")
    return re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")


class OddsQuote(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: MatchId = Field(default_factory=uuid4)
    match_id: MatchId
    bookmaker: str = Field(min_length=1, max_length=50)
    market: str = Field(min_length=1, max_length=50)
    outcome: str = Field(min_length=1, max_length=50)
    decimal_odds: float = Field(ge=1.01, le=1000.0)
    snapshot_taken_at: datetime

    @model_validator(mode="after")
    def _validate(self) -> "OddsQuote":
        if self.snapshot_taken_at.tzinfo is None:
            raise ValueError("snapshot_taken_at must be timezone-aware")
        return self

    def implied_probability(self) -> float:
        """Naive implied probability (does NOT remove overround)."""
        return 1.0 / self.decimal_odds


__all__ = ["BookmakerKey", "OddsQuote"]
