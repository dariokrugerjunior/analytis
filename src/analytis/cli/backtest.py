"""CLI for walk-forward backtests."""

import asyncio
from datetime import UTC, datetime

import typer
from rich.console import Console

from analytis.application.backtest import BacktestParams, BacktestUseCase
from analytis.config import get_settings
from analytis.persistence.engine import create_engine, create_session_factory

app = typer.Typer(help="Walk-forward backtests.")
console = Console()


@app.command("run")
def run_backtest(
    since: str = typer.Option("2010-01-01", help="Window start (YYYY-MM-DD)."),
    until: str = typer.Option("2026-06-12", help="Window end (YYYY-MM-DD)."),
    min_train_size: int = typer.Option(200, help="Min training matches."),
    test_size: int = typer.Option(50, help="Matches per test fold."),
    max_iter: int = typer.Option(200, help="L-BFGS max iter."),
    decay_per_day: float = typer.Option(0.005, help="Time decay."),
) -> None:
    """Run a walk-forward backtest and write a JSON report."""
    asyncio.run(_run(since, until, min_train_size, test_size, max_iter, decay_per_day))


async def _run(
    since: str,
    until: str,
    min_train_size: int,
    test_size: int,
    max_iter: int,
    decay_per_day: float,
) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        use_case = BacktestUseCase(factory)
        result = await use_case.execute(
            BacktestParams(
                since=datetime.fromisoformat(since).replace(tzinfo=UTC),
                until=datetime.fromisoformat(until).replace(tzinfo=UTC),
                min_train_size=min_train_size,
                test_size=test_size,
                max_iter=max_iter,
                decay_per_day=decay_per_day,
            )
        )
        console.print(
            f"[green]{result.n_slices} slices, "
            f"{result.total_test_matches} test matches.[/green]"
        )
        console.print(f"  report: {result.report_path}")
        for k, v in sorted(result.metrics.items()):
            console.print(f"  {k}: {v:.4f}")
    finally:
        await engine.dispose()
