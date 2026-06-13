"""CLI entry point."""

import typer

from analytis.cli import api, db
from analytis.config import get_settings
from analytis.logging import configure_logging

app = typer.Typer(
    name="analytis",
    help="Football analytics backend — predictions, ingestion, modeling.",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(db.app, name="db", help="Database operations.")
app.add_typer(api.app, name="api", help="HTTP API server.")


@app.callback()
def _root_callback() -> None:
    """Configure logging before any command runs."""
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)


if __name__ == "__main__":
    app()
