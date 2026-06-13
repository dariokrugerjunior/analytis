"""ORM model for ELO rating history."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from analytis.persistence.orm.base import Base, TimestampMixin


class EloHistoryORM(Base, TimestampMixin):
    __tablename__ = "elo_history"
    __table_args__ = (Index("ix_elo_history_team_as_of", "team_id", "as_of"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    team_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("team.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    games_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
