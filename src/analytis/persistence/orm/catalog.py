"""ORM models for catalog entities."""

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from analytis.persistence.orm.base import Base, TimestampMixin


class CompetitionORM(Base, TimestampMixin):
    __tablename__ = "competition"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    competition_type: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)

    seasons: Mapped[list["SeasonORM"]] = relationship(back_populates="competition")


class SeasonORM(Base, TimestampMixin):
    __tablename__ = "season"
    __table_args__ = (UniqueConstraint("competition_id", "label"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    competition_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("competition.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)

    competition: Mapped[CompetitionORM] = relationship(back_populates="seasons")


class TeamORM(Base, TimestampMixin):
    __tablename__ = "team"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    short_name: Mapped[str] = mapped_column(String(50), nullable=False)
    team_type: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)


class PlayerORM(Base, TimestampMixin):
    __tablename__ = "player"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(10), nullable=True)
    position: Mapped[str | None] = mapped_column(String(10), nullable=True)
    preferred_foot: Mapped[str | None] = mapped_column(String(10), nullable=True)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)


class VenueORM(Base, TimestampMixin):
    __tablename__ = "venue"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    altitude_m: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)


class RefereeORM(Base, TimestampMixin):
    __tablename__ = "referee"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    cards_per_game: Mapped[float | None] = mapped_column(nullable=True)
    penalties_per_game: Mapped[float | None] = mapped_column(nullable=True)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)


__all__: list[Any] = [
    "CompetitionORM",
    "PlayerORM",
    "RefereeORM",
    "SeasonORM",
    "TeamORM",
    "VenueORM",
]
