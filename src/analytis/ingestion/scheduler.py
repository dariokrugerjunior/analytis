"""APScheduler wiring — registers ingestion jobs on a single embedded scheduler."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from analytis.logging import get_logger

logger = get_logger(__name__)


@dataclass
class JobSpec:
    name: str
    fn: Callable[[], Awaitable[None]]
    cron: str | None = None
    interval_seconds: int | None = None


def build_scheduler(jobs: list[JobSpec]) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    for job in jobs:
        if job.cron:
            trigger = CronTrigger.from_crontab(job.cron)
        elif job.interval_seconds:
            trigger = IntervalTrigger(seconds=job.interval_seconds)
        else:
            raise ValueError(f"job {job.name} must define cron or interval_seconds")
        scheduler.add_job(
            job.fn,
            trigger=trigger,
            id=job.name,
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info("scheduler.job_registered", job=job.name)
    return scheduler
