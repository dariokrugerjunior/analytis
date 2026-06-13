"""FastAPI application factory."""

from fastapi import FastAPI

from analytis import __version__
from analytis.api.routes import health


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
    return app


app = create_app()
