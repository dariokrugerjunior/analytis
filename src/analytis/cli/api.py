"""CLI commands for the HTTP API server."""

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
    uvicorn.run(
        "analytis.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_config=None,
    )
