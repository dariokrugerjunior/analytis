"""Referee domain entity."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from analytis.domain.ids import RefereeId


class Referee(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: RefereeId = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    country: str = Field(min_length=2, max_length=10)
    cards_per_game: float | None = Field(default=None, ge=0)
    penalties_per_game: float | None = Field(default=None, ge=0)
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
