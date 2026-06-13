"""Repository for ingestion observability tables."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.domain.ingestion import (
    DataSource,
    IngestionRun,
    IngestionStatus,
)
from analytis.persistence.orm.ingestion import DataSourceORM, IngestionRunORM


class DataSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, ds: DataSource) -> None:
        stmt = pg_insert(DataSourceORM).values(
            source_id=ds.source_id,
            display_name=ds.display_name,
            homepage_url=ds.homepage_url,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["source_id"],
            set_={
                "display_name": stmt.excluded.display_name,
                "homepage_url": stmt.excluded.homepage_url,
            },
        )
        await self._session.execute(stmt)


class IngestionRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(self, data_source_id: str, job_name: str) -> IngestionRun:
        run = IngestionRun(
            data_source_id=data_source_id,
            job_name=job_name,
            started_at=datetime.now(UTC),
        )
        self._session.add(
            IngestionRunORM(
                id=run.id,
                data_source_id=run.data_source_id,
                job_name=run.job_name,
                started_at=run.started_at,
                status=run.status.value,
                records_touched=0,
            )
        )
        return run

    async def mark_succeeded(
        self, run_id: UUID, records_touched: int, payload_hash: str | None = None
    ) -> None:
        orm = await self._session.get(IngestionRunORM, run_id)
        if orm is None:
            raise ValueError(f"IngestionRun {run_id} not found")
        orm.status = IngestionStatus.SUCCEEDED.value
        orm.finished_at = datetime.now(UTC)
        orm.records_touched = records_touched
        orm.payload_hash = payload_hash

    async def mark_failed(self, run_id: UUID, error: str) -> None:
        orm = await self._session.get(IngestionRunORM, run_id)
        if orm is None:
            raise ValueError(f"IngestionRun {run_id} not found")
        orm.status = IngestionStatus.FAILED.value
        orm.finished_at = datetime.now(UTC)
        orm.error_message = error
