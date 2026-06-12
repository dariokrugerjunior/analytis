"""Player domain entity."""

from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from analytis.domain.ids import PlayerId


class PreferredFoot(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"


class Player(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: PlayerId = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    date_of_birth: date | None = None
    nationality: str | None = Field(default=None, max_length=10)
    position: str | None = Field(default=None, max_length=10)
    preferred_foot: PreferredFoot | None = None
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
