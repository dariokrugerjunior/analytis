"""Repository pattern — hides ORM details from the rest of the system."""

from analytis.persistence.repositories.bets import ValueBetRepository
from analytis.persistence.repositories.competition import CompetitionRepository
from analytis.persistence.repositories.elo import EloHistoryRepository
from analytis.persistence.repositories.feature_snapshot import (
    FeatureSnapshotRepository,
)
from analytis.persistence.repositories.ingestion import (
    DataSourceRepository,
    IngestionRunRepository,
)
from analytis.persistence.repositories.match import MatchRepository
from analytis.persistence.repositories.model_version import ModelVersionRepository
from analytis.persistence.repositories.odds import OddsRepository
from analytis.persistence.repositories.reference import SeasonRepository
from analytis.persistence.repositories.team import TeamRepository

__all__ = [
    "CompetitionRepository",
    "DataSourceRepository",
    "EloHistoryRepository",
    "FeatureSnapshotRepository",
    "IngestionRunRepository",
    "MatchRepository",
    "ModelVersionRepository",
    "OddsRepository",
    "SeasonRepository",
    "TeamRepository",
    "ValueBetRepository",
]
