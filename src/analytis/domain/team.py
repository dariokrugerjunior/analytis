"""Team domain entity."""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from analytis.domain.ids import TeamId


class TeamType(StrEnum):
    SELECAO = "selecao"
    CLUBE = "clube"


class Team(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: TeamId = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    short_name: str = Field(min_length=1, max_length=50)
    team_type: TeamType
    country: str = Field(min_length=2, max_length=10)
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
