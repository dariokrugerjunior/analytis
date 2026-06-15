"""Background job: re-ingest fixtures when there are matches near kickoff.

Keeps the UI honest in real time without forcing the operator to run
`analytis ingest fixtures` by hand every few minutes during games.

The job only hits Football-Data.org when there is at least one match
inside the live window [-after_kickoff_minutes, +before_kickoff_minutes]
relative to `now`, so it stays well below the free-tier rate limit
when nothing is playing.
"""

from datetime import UTC, datetime, timedelta

import httpx
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from analytis.application.ingest_fixtures import (
    FixturesParams,
    IngestFixturesUseCase,
)
from analytis.config import Settings
from analytis.ingestion.adapters.football_data import FootballDataAdapter
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.matches import MatchORM

log = structlog.get_logger(__name__)


class AutoIngestJob:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: AsyncEngine | None = None
        self._factory: async_sessionmaker[AsyncSession] | None = None

    async def _ensure_engine(self) -> async_sessionmaker[AsyncSession]:
        if self._factory is None:
            self._engine = create_engine(self._settings)
            self._factory = create_session_factory(self._engine)
        return self._factory

    async def _has_live_match(self, factory: async_sessionmaker[AsyncSession]) -> bool:
        now = datetime.now(UTC)
        window_start = now - timedelta(
            minutes=self._settings.auto_ingest_window_after_kickoff_minutes
        )
        window_end = now + timedelta(
            minutes=self._settings.auto_ingest_window_before_kickoff_minutes
        )
        async with factory() as session:
            stmt = (
                select(MatchORM.id)
                .where(
                    MatchORM.kickoff_utc >= window_start,
                    MatchORM.kickoff_utc <= window_end,
                    MatchORM.status.in_(("scheduled", "live")),
                )
                .limit(1)
            )
            row = (await session.scalars(stmt)).first()
            return row is not None

    async def run(self) -> None:
        if self._settings.football_data_api_key is None:
            return
        factory = await self._ensure_engine()
        try:
            if not await self._has_live_match(factory):
                return
            async with httpx.AsyncClient(
                base_url=FootballDataAdapter.BASE_URL, timeout=30.0
            ) as client:
                adapter = FootballDataAdapter(
                    client=client,
                    api_key=self._settings.football_data_api_key.get_secret_value(),
                )
                use_case = IngestFixturesUseCase(factory, adapter)
                result = await use_case.execute(
                    FixturesParams(
                        competition_external_id=self._settings.auto_ingest_competition,
                        season_label=self._settings.auto_ingest_season,
                    )
                )
            log.info(
                "auto_ingest_tick",
                records=result.records_touched,
                competition=self._settings.auto_ingest_competition,
                season=self._settings.auto_ingest_season,
            )
        except Exception as exc:
            log.warning("auto_ingest_failed", error=str(exc))

    async def aclose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._factory = None


def build_scheduler(settings: Settings) -> tuple[AsyncIOScheduler, AutoIngestJob] | None:
    if not settings.auto_ingest_enabled:
        return None
    if settings.football_data_api_key is None:
        return None
    job = AutoIngestJob(settings)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        job.run,
        trigger="interval",
        seconds=settings.auto_ingest_interval_seconds,
        next_run_time=datetime.now(UTC),
        coalesce=True,
        max_instances=1,
        id="auto_ingest_fixtures",
    )
    return scheduler, job
