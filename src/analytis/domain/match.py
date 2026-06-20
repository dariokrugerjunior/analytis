"""Match domain entity."""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from analytis.domain.ids import (
    MatchId,
    RefereeId,
    SeasonId,
    TeamId,
    VenueId,
)


class MatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class Match(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: MatchId = Field(default_factory=uuid4)
    season_id: SeasonId
    home_team_id: TeamId
    away_team_id: TeamId
    kickoff_utc: datetime
    venue_id: VenueId | None = None
    referee_id: RefereeId | None = None
    is_home_neutral: bool = False
    status: MatchStatus = MatchStatus.SCHEDULED
    stage: str | None = None
    home_goals: int | None = Field(default=None, ge=0)
    away_goals: int | None = Field(default=None, ge=0)
    home_corners: int | None = Field(default=None, ge=0)
    away_corners: int | None = Field(default=None, ge=0)
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_business_rules(self) -> "Match":
        if self.home_team_id == self.away_team_id:
            raise ValueError("a team cannot play itself")
        if self.kickoff_utc.tzinfo is None:
            raise ValueError("kickoff_utc must be timezone-aware UTC")
        if self.status is MatchStatus.FINISHED and (
            self.home_goals is None or self.away_goals is None
        ):
            raise ValueError("finished match requires goals on both sides")
        return self
