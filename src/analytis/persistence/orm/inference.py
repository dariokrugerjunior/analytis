"""ORM models for inference-side entities (snapshots, models, predictions)."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from analytis.persistence.orm.base import Base, TimestampMixin


class FeatureSnapshotORM(Base):
    __tablename__ = "feature_snapshot"
    __table_args__ = (Index("ix_feature_snapshot_match", "match_id", "snapshot_taken_at"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("match.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(nullable=False)
    code_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelVersionORM(Base, TimestampMixin):
    __tablename__ = "model_version"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    family: Mapped[str] = mapped_column(String(100), nullable=False)
    git_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    hyperparams: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_promoted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PredictionORM(Base):
    __tablename__ = "prediction"
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "market",
            "outcome",
            "model_version_id",
            "feature_snapshot_id",
        ),
        CheckConstraint("prob >= 0.0 AND prob <= 1.0", name="prob_range"),
        CheckConstraint("ci_low <= ci_high", name="ci_ordered"),
        Index("ix_prediction_match_market", "match_id", "market"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("match.id", ondelete="CASCADE"),
        nullable=False,
    )
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    prob: Mapped[float] = mapped_column(Float, nullable=False)
    ci_low: Mapped[float] = mapped_column(Float, nullable=False)
    ci_high: Mapped[float] = mapped_column(Float, nullable=False)
    model_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_version.id", ondelete="RESTRICT"),
        nullable=False,
    )
    feature_snapshot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("feature_snapshot.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
