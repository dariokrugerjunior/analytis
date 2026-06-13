"""CLI for finding value bets."""

import asyncio
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from analytis.application.find_value_bets import (
    FindValueBetsParams,
    FindValueBetsUseCase,
)
from analytis.config import get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.bets import ValueBetORM
from analytis.persistence.orm.inference import ModelVersionORM

app = typer.Typer(help="Value bet discovery.")
console = Console()


@app.command("find-value")
def find_value(
    match_id: str = typer.Option(..., help="Match UUID."),
    model: str = typer.Option(..., "--model", help="ModelVersion name."),
    min_edge: float = typer.Option(0.03, help="Minimum edge to consider a bet."),
    bankroll: float = typer.Option(1000.0, help="Bankroll size."),
    fraction: float = typer.Option(0.25, help="Kelly fraction (0.25 = quarter)."),
    max_units: float = typer.Option(50.0, help="Max units per bet."),
) -> None:
    """Find +EV bets for a match using current odds."""
    asyncio.run(_find(match_id, model, min_edge, bankroll, fraction, max_units))


async def _find(
    match_id_str: str,
    model_name: str,
    min_edge: float,
    bankroll: float,
    fraction: float,
    max_units: float,
) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as s:
            mv = (
                await s.scalars(select(ModelVersionORM).where(ModelVersionORM.name == model_name))
            ).one_or_none()
            if mv is None:
                console.print(f"[red]Model {model_name!r} not found[/red]")
                raise typer.Exit(code=2)
            mv_id = mv.id
            mv_name = mv.name

        use_case = FindValueBetsUseCase(factory)
        result = await use_case.execute(
            FindValueBetsParams(
                match_id=UUID(match_id_str),
                model_version_id=mv_id,
                min_edge=min_edge,
                bankroll=bankroll,
                kelly_fraction_value=fraction,
                max_units_per_bet=max_units,
            )
        )
        async with factory() as s:
            bets = (
                await s.scalars(
                    select(ValueBetORM).where(ValueBetORM.match_id == UUID(match_id_str))
                )
            ).all()

        table = Table(title=f"Value Bets ({mv_name})")
        table.add_column("Market")
        table.add_column("Outcome")
        table.add_column("Book")
        table.add_column("Odds")
        table.add_column("Our %")
        table.add_column("Mkt %")
        table.add_column("Edge")
        table.add_column("Stake (u)")
        for b in bets:
            table.add_row(
                b.market,
                b.outcome,
                b.bookmaker,
                f"{b.decimal_odds:.2f}",
                f"{b.our_prob * 100:.1f}",
                f"{b.market_prob * 100:.1f}",
                f"{b.edge * 100:+.1f}%",
                f"{b.suggested_stake_units:.1f}",
            )
        console.print(table)
        console.print(f"[green]{result.bets_found} new bets found this run.[/green]")
    finally:
        await engine.dispose()
