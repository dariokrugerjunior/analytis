"""Venue (stadium) domain entity."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from analytis.domain.ids import VenueId


class Venue(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: VenueId = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=2, max_length=10)
    altitude_m: int = Field(default=0, ge=0)
    capacity: int | None = Field(default=None, ge=0)
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
