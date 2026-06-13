"""Repository pattern — hides ORM details from the rest of the system."""

from analytis.persistence.repositories.competition import CompetitionRepository
from analytis.persistence.repositories.elo import EloHistoryRepository
from analytis.persistence.repositories.ingestion import (
    DataSourceRepository,
    IngestionRunRepository,
)
from analytis.persistence.repositories.match import MatchRepository
from analytis.persistence.repositories.reference import SeasonRepository
from analytis.persistence.repositories.team import TeamRepository

__all__ = [
    "CompetitionRepository",
    "DataSourceRepository",
    "EloHistoryRepository",
    "IngestionRunRepository",
    "MatchRepository",
    "SeasonRepository",
    "TeamRepository",
]
