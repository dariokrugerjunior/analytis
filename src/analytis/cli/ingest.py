"""CLI commands for data ingestion."""

import asyncio

import httpx
import typer
from rich.console import Console

from analytis.application.ingest_fixtures import (
    FixturesParams,
    IngestFixturesUseCase,
)
from analytis.config import get_settings
from analytis.ingestion.adapters.football_data import FootballDataAdapter
from analytis.persistence.engine import create_engine, create_session_factory

app = typer.Typer(help="Data ingestion commands.")
console = Console()


@app.command()
def fixtures(
    competition: str = typer.Option(
        ..., "--competition", help="Football-Data competition id (e.g. 2000 for World Cup)."
    ),
    season: str = typer.Option(..., "--season", help="Season label (e.g. 2026)."),
) -> None:
    """Ingest fixtures and results for a competition/season."""
    asyncio.run(_fixtures(competition, season))


async def _fixtures(competition: str, season: str) -> None:
    settings = get_settings()
    if settings.football_data_api_key is None:
        console.print("[red]ANALYTIS_FOOTBALL_DATA_API_KEY not set[/red]")
        raise typer.Exit(code=2)

    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with httpx.AsyncClient(base_url=FootballDataAdapter.BASE_URL, timeout=30.0) as client:
            adapter = FootballDataAdapter(
                client=client,
                api_key=settings.football_data_api_key.get_secret_value(),
            )
            use_case = IngestFixturesUseCase(factory, adapter)
            result = await use_case.execute(FixturesParams(competition, season))
        console.print(
            f"[green]Ingested {result.records_touched} matches "
            f"for competition={competition} season={season}[/green]"
        )
    finally:
        await engine.dispose()


@app.command()
def backfill(
    competition: str = typer.Option(..., "--competition"),
    seasons: list[str] = typer.Option(  # noqa: B008
        ..., "--season", help="Repeat for each season."
    ),
) -> None:
    """Backfill multiple seasons of a competition (sequential)."""
    asyncio.run(_backfill(competition, seasons))


async def _backfill(competition: str, seasons: list[str]) -> None:
    settings = get_settings()
    if settings.football_data_api_key is None:
        console.print("[red]ANALYTIS_FOOTBALL_DATA_API_KEY not set[/red]")
        raise typer.Exit(code=2)
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with httpx.AsyncClient(base_url=FootballDataAdapter.BASE_URL, timeout=30.0) as client:
            adapter = FootballDataAdapter(
                client=client,
                api_key=settings.football_data_api_key.get_secret_value(),
            )
            use_case = IngestFixturesUseCase(factory, adapter)
            total = 0
            for season in seasons:
                console.print(f"-> season={season}")
                result = await use_case.execute(FixturesParams(competition, season))
                total += result.records_touched
                console.print(f"   {result.records_touched} matches")
        console.print(f"[green]Backfill total: {total} matches[/green]")
    finally:
        await engine.dispose()


@app.command()
def history(
    tournament: list[str] = typer.Option(  # noqa: B008
        ["FIFA World Cup"], "--tournament", help="Tournament name(s) to filter."
    ),
    since: str = typer.Option("2010-01-01", help="Minimum date (YYYY-MM-DD)."),
) -> None:
    """Ingest international match history from the open CSV dataset."""
    asyncio.run(_history(tournament, since))


async def _history(tournaments: list[str], since: str) -> None:
    from datetime import UTC
    from datetime import datetime as _dt

    from analytis.application.ingest_international_history import (
        IngestInternationalHistoryUseCase,
        InternationalHistoryParams,
    )
    from analytis.ingestion.adapters.international_results import (
        InternationalResultsAdapter,
    )

    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            adapter = InternationalResultsAdapter(client=client)
            use_case = IngestInternationalHistoryUseCase(factory, adapter)
            params = InternationalHistoryParams(
                tournaments=set(tournaments),
                min_date=_dt.fromisoformat(since).replace(tzinfo=UTC),
            )
            result = await use_case.execute(params)
        console.print(
            f"[green]Ingested {result.records_touched} historical matches "
            f"({', '.join(sorted(tournaments))} since {since})[/green]"
        )
    finally:
        await engine.dispose()
