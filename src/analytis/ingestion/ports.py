"""Ports for ingestion adapters — defines the contract every source must honor."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class CompetitionDTO:
    source_id: str
    external_id: str
    name: str
    slug: str
    competition_type: str  # "selecao" | "clube"
    country: str


@dataclass(frozen=True)
class SeasonDTO:
    source_id: str
    competition_external_id: str
    label: str
    start_date: date | None
    end_date: date | None


@dataclass(frozen=True)
class TeamDTO:
    source_id: str
    external_id: str
    name: str
    short_name: str
    team_type: str
    country: str


@dataclass(frozen=True)
class MatchDTO:
    source_id: str
    external_id: str
    competition_external_id: str
    season_label: str
    home_team_external_id: str
    home_team_name: str
    home_team_short_name: str
    away_team_external_id: str
    away_team_name: str
    away_team_short_name: str
    kickoff_utc: datetime
    is_home_neutral: bool
    status: str
    home_goals: int | None
    away_goals: int | None
    home_corners: int | None
    away_corners: int | None
    venue_name: str | None
    referee_name: str | None


@dataclass(frozen=True)
class EloRatingDTO:
    source_id: str
    team_name: str
    country_code: str
    rating: float
    as_of: date


class DataSourceAdapter(Protocol):
    """Common contract every external source adapter must implement."""

    source_id: str

    def fetch_competitions(self) -> Iterable[CompetitionDTO]: ...

    def fetch_seasons(self, competition_external_id: str) -> Iterable[SeasonDTO]: ...

    def fetch_teams(self, competition_external_id: str) -> Iterable[TeamDTO]: ...

    def fetch_matches(
        self, competition_external_id: str, season_label: str
    ) -> Iterable[MatchDTO]: ...
