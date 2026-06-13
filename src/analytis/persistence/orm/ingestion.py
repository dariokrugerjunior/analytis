"""ORM models for ingestion observability."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from analytis.persistence.orm.base import Base, TimestampMixin


class DataSourceORM(Base, TimestampMixin):
    __tablename__ = "data_source"

    source_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    homepage_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class IngestionRunORM(Base):
    __tablename__ = "ingestion_run"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    data_source_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    job_name: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    records_touched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
