"""ORM for odds snapshots."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
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


class OddsSnapshotORM(Base, TimestampMixin):
    __tablename__ = "odds_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "bookmaker",
            "market",
            "outcome",
            "snapshot_taken_at",
            name="uq_odds_snapshot_natural",
        ),
        Index("ix_odds_snapshot_match_market", "match_id", "market"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("match.id", ondelete="CASCADE"),
        nullable=False,
    )
    bookmaker: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    decimal_odds: Mapped[float] = mapped_column(Float, nullable=False)
    snapshot_taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
