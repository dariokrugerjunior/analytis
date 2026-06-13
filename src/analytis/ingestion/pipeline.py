"""Generic ingestion pipeline — wraps a job in run tracking."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.logging import get_logger
from analytis.persistence.repositories import IngestionRunRepository
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass
class IngestionResult:
    records_touched: int
    payload_hash: str | None = None


JobFn = Callable[[UnitOfWork], Awaitable[IngestionResult]]


class IngestionPipeline:
    """Runs an ingestion job inside a UnitOfWork with start/succeed/fail tracking."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        data_source_id: str,
    ) -> None:
        self._factory = session_factory
        self._source = data_source_id
        self._log: structlog.stdlib.BoundLogger = get_logger(__name__).bind(source=data_source_id)

    async def run(self, job_name: str, job: JobFn) -> IngestionResult:
        async with UnitOfWork(self._factory) as run_uow:
            run = await IngestionRunRepository(run_uow.session).start(self._source, job_name)
        run_id = run.id
        self._log.info("ingestion_start", job=job_name, run_id=str(run_id))

        try:
            async with UnitOfWork(self._factory) as work_uow:
                result = await job(work_uow)

            async with UnitOfWork(self._factory) as finish_uow:
                await IngestionRunRepository(finish_uow.session).mark_succeeded(
                    run_id, result.records_touched, result.payload_hash
                )
            self._log.info(
                "ingestion_succeeded",
                job=job_name,
                records=result.records_touched,
            )
            return result
        except Exception as exc:
            async with UnitOfWork(self._factory) as finish_uow:
                await IngestionRunRepository(finish_uow.session).mark_failed(run_id, str(exc))
            self._log.error("ingestion_failed", job=job_name, error=str(exc))
            raise
