"""CLI commands for model training."""

import asyncio
from datetime import UTC, datetime

import typer
from rich.console import Console

from analytis.application.train_dixon_coles import (
    TrainDixonColesParams,
    TrainDixonColesUseCase,
)
from analytis.application.train_xgboost import (
    TrainXGBoostParams,
    TrainXGBoostUseCase,
)
from analytis.config import get_settings
from analytis.persistence.engine import create_engine, create_session_factory

app = typer.Typer(help="Model training commands.")
console = Console()


@app.command("dixon-coles")
def dixon_coles(
    since: str = typer.Option("2010-01-01", help="Min match date (YYYY-MM-DD)."),
    name: str = typer.Option(..., "--name", help="ModelVersion name."),
    max_iter: int = typer.Option(200, help="L-BFGS max iterations."),
    decay_per_day: float = typer.Option(0.005, help="Time-decay weight per day."),
) -> None:
    """Train a Dixon-Coles model from finished matches in the DB."""
    asyncio.run(_run(since, name, max_iter, decay_per_day))


async def _run(since: str, name: str, max_iter: int, decay_per_day: float) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        use_case = TrainDixonColesUseCase(factory)
        result = await use_case.execute(
            TrainDixonColesParams(
                since=datetime.fromisoformat(since).replace(tzinfo=UTC),
                name=name,
                max_iter=max_iter,
                decay_per_day=decay_per_day,
            )
        )
        console.print(
            f"[green]Trained {result.match_count} matches across {result.team_count} teams.[/green]"
        )
        console.print(f"  version_id={result.version_id}  artifact={result.artifact_path}")
        console.print(f"  home_advantage={result.home_advantage:.3f}  rho={result.rho:.3f}")
    finally:
        await engine.dispose()


@app.command("xgboost")
def xgboost_train(
    since: str = typer.Option("2010-01-01", help="Min match date (YYYY-MM-DD)."),
    name: str = typer.Option(..., "--name", help="ModelVersion name."),
    market: str = typer.Option("1x2", help="Market: 1x2, over_under_2_5, btts."),
    n_estimators: int = typer.Option(200, help="XGBoost n_estimators."),
    max_depth: int = typer.Option(4, help="XGBoost max_depth."),
    learning_rate: float = typer.Option(0.05, help="XGBoost learning_rate."),
) -> None:
    """Train an XGBoost classifier from features over finished matches."""
    asyncio.run(_run_xgb(since, name, market, n_estimators, max_depth, learning_rate))


async def _run_xgb(
    since: str,
    name: str,
    market: str,
    n_estimators: int,
    max_depth: int,
    learning_rate: float,
) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        use_case = TrainXGBoostUseCase(factory)
        result = await use_case.execute(
            TrainXGBoostParams(
                since=datetime.fromisoformat(since).replace(tzinfo=UTC),
                name=name,
                market=market,
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
            )
        )
        console.print(
            f"[green]Trained XGBoost ({market}) on {result.n_samples} samples "
            f"with {result.n_features} features.[/green]"
        )
        console.print(f"  version_id={result.version_id}  artifact={result.artifact_path}")
    finally:
        await engine.dispose()
