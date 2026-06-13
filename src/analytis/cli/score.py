"""CLI commands for scoring matches."""

import asyncio
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from analytis.application.score_match import ScoreMatchParams, ScoreMatchUseCase
from analytis.config import get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.inference import ModelVersionORM
from analytis.persistence.orm.matches import MatchORM

app = typer.Typer(help="Scoring commands.")
console = Console()


@app.command("match")
def score_one(
    match_id: str = typer.Option(..., help="Match UUID."),
    model: str = typer.Option(..., "--model", help="ModelVersion name."),
) -> None:
    """Score a single match."""
    asyncio.run(_score_one(match_id, model))


async def _score_one(match_id_str: str, model_name: str) -> None:
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

        use_case = ScoreMatchUseCase(factory)
        result = await use_case.execute(
            ScoreMatchParams(
                match_id=UUID(match_id_str),
                model_version_id=mv_id,
            )
        )

        table = Table(title=f"Predictions ({mv.name})")
        table.add_column("Market")
        table.add_column("Outcome")
        table.add_column("Prob")
        table.add_row("1X2", "home", f"{result.home_prob:.3f}")
        table.add_row("1X2", "draw", f"{result.draw_prob:.3f}")
        table.add_row("1X2", "away", f"{result.away_prob:.3f}")
        table.add_row("OU 2.5", "over", f"{result.over_2_5_prob:.3f}")
        table.add_row("BTTS", "yes", f"{result.btts_yes_prob:.3f}")
        console.print(table)
        console.print(f"[green]{result.predictions_inserted} predictions inserted.[/green]")
    finally:
        await engine.dispose()


@app.command("all-upcoming")
def score_upcoming(
    model: str = typer.Option(..., "--model", help="ModelVersion name."),
) -> None:
    """Score every scheduled match with this model."""
    asyncio.run(_score_upcoming(model))


async def _score_upcoming(model_name: str) -> None:
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

            matches = (
                await s.scalars(select(MatchORM).where(MatchORM.status == "scheduled"))
            ).all()

        use_case = ScoreMatchUseCase(factory)
        scored = 0
        skipped = 0
        for m in matches:
            try:
                await use_case.execute(
                    ScoreMatchParams(
                        match_id=m.id,
                        model_version_id=mv_id,
                    )
                )
                scored += 1
            except ValueError as exc:
                skipped += 1
                console.print(f"[yellow]skipped {m.id}: {exc}[/yellow]")
        console.print(f"[green]Scored {scored} matches, skipped {skipped}.[/green]")
    finally:
        await engine.dispose()
