"""Inference-side domain entities: feature snapshots, model versions, predictions."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from analytis.domain.ids import (
    FeatureSnapshotId,
    MatchId,
    ModelVersionId,
    PredictionId,
)


class PredictionMarket(StrEnum):
    MATCH_RESULT = "1x2"
    OVER_UNDER_GOALS = "over_under_goals"
    BTTS = "btts"
    CORNERS_TOTAL = "corners_total"


class FeatureSnapshot(BaseModel):
    """Immutable snapshot of all features used in one scoring pass."""

    model_config = ConfigDict(frozen=True)

    id: FeatureSnapshotId = Field(default_factory=uuid4)
    match_id: MatchId
    snapshot_taken_at: datetime
    features: dict[str, Any]
    code_version: str | None = None

    @model_validator(mode="after")
    def _validate_aware(self) -> "FeatureSnapshot":
        if self.snapshot_taken_at.tzinfo is None:
            raise ValueError("snapshot_taken_at must be timezone-aware")
        return self


class ModelVersion(BaseModel):
    """Versioned, persisted record of a trained model."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: ModelVersionId = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    family: str = Field(min_length=1, max_length=100)
    git_sha: str = Field(min_length=4, max_length=40)
    hyperparams: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    artifact_path: str | None = None
    trained_at: datetime | None = None
    is_promoted: bool = False


class Prediction(BaseModel):
    """Immutable prediction for one (match, market, outcome) tuple."""

    model_config = ConfigDict(frozen=True)

    id: PredictionId = Field(default_factory=uuid4)
    match_id: MatchId
    market: PredictionMarket
    outcome: str = Field(min_length=1, max_length=50)
    prob: float = Field(ge=0.0, le=1.0)
    ci_low: float = Field(ge=0.0, le=1.0)
    ci_high: float = Field(ge=0.0, le=1.0)
    model_version_id: ModelVersionId
    feature_snapshot_id: FeatureSnapshotId
    created_at: datetime

    @model_validator(mode="after")
    def _validate(self) -> "Prediction":
        if self.ci_low > self.ci_high:
            raise ValueError("ci_low must be <= ci_high")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self
