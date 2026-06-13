"""ORM for value bet recommendations + CLV tracking."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from analytis.persistence.orm.base import Base, TimestampMixin


class ValueBetORM(Base, TimestampMixin):
    __tablename__ = "value_bet"
    __table_args__ = (
        Index("ix_value_bet_match", "match_id"),
        Index("ix_value_bet_model", "model_version_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("match.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_version.id", ondelete="RESTRICT"),
        nullable=False,
    )
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    bookmaker: Mapped[str] = mapped_column(String(50), nullable=False)
    our_prob: Mapped[float] = mapped_column(Float, nullable=False)
    market_prob: Mapped[float] = mapped_column(Float, nullable=False)
    decimal_odds: Mapped[float] = mapped_column(Float, nullable=False)
    edge: Mapped[float] = mapped_column(Float, nullable=False)
    kelly_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    suggested_stake_units: Mapped[float] = mapped_column(Float, nullable=False)
    found_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closing_decimal_odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    closing_clv: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_realised: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
