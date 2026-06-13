"""ELO rating domain entity (one rating value at a point in time)."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from analytis.domain.ids import TeamId


class EloRating(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: TeamId = Field(default_factory=uuid4)
    team_id: TeamId
    rating: float = Field(ge=0.0, le=4000.0)
    as_of: datetime
    games_played: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate(self) -> "EloRating":
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return self
