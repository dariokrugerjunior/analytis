"""Competition domain entity."""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from analytis.domain.ids import CompetitionId


class CompetitionType(StrEnum):
    SELECAO = "selecao"
    CLUBE = "clube"


class Competition(BaseModel):
    """Top-level competition (league, cup, international tournament)."""

    model_config = ConfigDict(frozen=False, str_strip_whitespace=True)

    id: CompetitionId = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9\-]+$")
    competition_type: CompetitionType
    country: str = Field(min_length=2, max_length=10, description="ISO-3 or 'INTL'")
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
