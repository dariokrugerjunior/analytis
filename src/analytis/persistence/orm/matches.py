"""ORM models for matches and lineups."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from analytis.persistence.orm.base import Base, TimestampMixin


class MatchORM(Base, TimestampMixin):
    __tablename__ = "match"
    __table_args__ = (
        Index("ix_match_kickoff_utc", "kickoff_utc"),
        Index("ix_match_season_id", "season_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    season_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("season.id", ondelete="CASCADE"),
        nullable=False,
    )
    home_team_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("team.id", ondelete="RESTRICT"),
        nullable=False,
    )
    away_team_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("team.id", ondelete="RESTRICT"),
        nullable=False,
    )
    kickoff_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    venue_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("venue.id", ondelete="SET NULL"),
        nullable=True,
    )
    referee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("referee.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_home_neutral: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)

    lineups: Mapped[list["MatchLineupORM"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class MatchLineupORM(Base, TimestampMixin):
    __tablename__ = "match_lineup"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("match.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("team.id", ondelete="RESTRICT"),
        nullable=False,
    )
    formation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    players: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)
    """JSONB shape: {"starting": [player_id, ...], "bench": [...]}"""

    match: Mapped[MatchORM] = relationship(back_populates="lineups")
