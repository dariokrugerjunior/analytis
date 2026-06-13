"""CLI for odds ingestion."""

import asyncio

import httpx
import typer
from rich.console import Console

from analytis.application.ingest_odds import IngestOddsParams, IngestOddsUseCase
from analytis.config import get_settings
from analytis.ingestion.adapters.the_odds_api import TheOddsApiAdapter
from analytis.persistence.engine import create_engine, create_session_factory

app = typer.Typer(help="Odds ingestion.")
console = Console()


@app.command("fetch")
def fetch(
    sport_key: str = typer.Option(
        "soccer_fifa_world_cup", "--sport", help="The Odds API sport key."
    ),
) -> None:
    """Fetch current odds from The Odds API."""
    asyncio.run(_fetch(sport_key))


async def _fetch(sport_key: str) -> None:
    settings = get_settings()
    if settings.the_odds_api_key is None:
        console.print("[red]ANALYTIS_THE_ODDS_API_KEY not set[/red]")
        raise typer.Exit(code=2)
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with httpx.AsyncClient(base_url=settings.the_odds_api_base_url) as client:
            adapter = TheOddsApiAdapter(
                client=client,
                api_key=settings.the_odds_api_key.get_secret_value(),
            )
            use_case = IngestOddsUseCase(factory, adapter)
            result = await use_case.execute(IngestOddsParams(sport_key=sport_key))
        console.print(f"[green]Inserted {result.records_touched} new odds quotes.[/green]")
    finally:
        await engine.dispose()
