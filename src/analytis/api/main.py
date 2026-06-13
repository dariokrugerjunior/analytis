"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from analytis import __version__
from analytis.api.routes import health, matches, models, odds, predictions, value_bets


def create_app() -> FastAPI:
    app = FastAPI(
        title="analytis",
        version=__version__,
        description="Football analytics backend — pre-match probabilistic predictions.",
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    app.include_router(health.router, prefix="/v1")
    app.include_router(matches.router, prefix="/v1")
    app.include_router(predictions.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")
    app.include_router(odds.router, prefix="/v1")
    app.include_router(value_bets.router, prefix="/v1")

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
