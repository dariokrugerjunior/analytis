"""Season domain entity."""

from datetime import date, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from analytis.domain.ids import CompetitionId, SeasonId


class Season(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: SeasonId = Field(default_factory=uuid4)
    competition_id: CompetitionId
    label: str = Field(min_length=1, max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
