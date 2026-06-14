"""CLI commands for the HTTP API server."""

import asyncio
import sys

import typer
import uvicorn

app = typer.Typer(help="HTTP API server.")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host."),
    port: int = typer.Option(8000, help="Bind port."),
    reload: bool = typer.Option(False, help="Enable auto-reload (dev only)."),
) -> None:
    """Start the FastAPI server."""
    if sys.platform == "win32":
        # psycopg async needs SelectorEventLoop; uvicorn forces Proactor by default.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        config = uvicorn.Config(
            "analytis.api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_config=None,
            loop="none",
        )
        asyncio.run(uvicorn.Server(config).serve())
    else:
        uvicorn.run(
            "analytis.api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_config=None,
        )
