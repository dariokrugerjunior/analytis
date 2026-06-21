"""CLI entry point."""

import asyncio
import sys

import typer

from analytis.cli import api, backtest, bets, db, frontend, ingest, odds, push, score, train
from analytis.config import get_settings
from analytis.logging import configure_logging

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = typer.Typer(
    name="analytis",
    help="Football analytics backend — predictions, ingestion, modeling.",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(db.app, name="db", help="Database operations.")
app.add_typer(api.app, name="api", help="HTTP API server.")
app.add_typer(ingest.app, name="ingest", help="Data ingestion.")
app.add_typer(train.app, name="train", help="Model training.")
app.add_typer(score.app, name="score", help="Score matches.")
app.add_typer(odds.app, name="odds", help="Odds ingestion.")
app.add_typer(backtest.app, name="backtest", help="Walk-forward backtests.")
app.add_typer(bets.app, name="bets", help="Value bet discovery.")
app.add_typer(push.app, name="push", help="Web Push notifications.")
app.add_typer(frontend.app, name="frontend", help="Frontend operations.")


@app.callback()
def _root_callback() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)


if __name__ == "__main__":
    app()
