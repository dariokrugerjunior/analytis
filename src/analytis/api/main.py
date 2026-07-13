"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from analytis import __version__
from analytis.api.auto_ingest import build_scheduler
from analytis.api.routes import (
    accuracy,
    dashboard,
    health,
    matches,
    models,
    odds,
    predictions,
    push,
    scoreline,
    value_bets,
)
from analytis.config import get_settings

log = structlog.get_logger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    built = build_scheduler(settings)
    if built is None:
        log.info("auto_ingest_disabled")
        yield
        return
    scheduler, job = built
    scheduler.start()
    log.info(
        "auto_ingest_started",
        interval_seconds=settings.auto_ingest_interval_seconds,
        competition=settings.auto_ingest_competition,
        season=settings.auto_ingest_season,
    )
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await job.aclose()
        log.info("auto_ingest_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="analytis",
        version=__version__,
        description="Football analytics backend — pre-match probabilistic predictions.",
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=_lifespan,
    )
    app.include_router(health.router, prefix="/v1")
    app.include_router(matches.router, prefix="/v1")
    app.include_router(predictions.router, prefix="/v1")
    app.include_router(scoreline.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")
    app.include_router(odds.router, prefix="/v1")
    app.include_router(value_bets.router, prefix="/v1")
    app.include_router(accuracy.router, prefix="/v1")
    app.include_router(dashboard.router, prefix="/v1")
    app.include_router(push.router, prefix="/v1")

    # Static frontend (after all /v1/* routes so they take priority).
    frontend_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    else:
        # Friendly fallback when frontend wasn't built yet.
        @app.get("/", include_in_schema=False, response_class=HTMLResponse)
        async def _index() -> HTMLResponse:
            return HTMLResponse(
                "<h1>analytis</h1>"
                "<p>Frontend not built. Run "
                "<code>uv run analytis frontend build</code> first, then reload.</p>",
                status_code=200,
            )

    return app


app = create_app()
