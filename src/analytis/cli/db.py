"""CLI commands for database management."""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Database operations.")
console = Console()


@app.command()
def migrate(
    revision: str = typer.Option("head", help="Alembic revision target."),
) -> None:
    """Apply Alembic migrations up to the target revision."""
    project_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", revision],
        cwd=project_root,
        check=False,
    )
    if result.returncode != 0:
        console.print("[red]Migration failed[/red]")
        sys.exit(result.returncode)
    console.print(f"[green]Migrated to {revision}[/green]")


@app.command()
def downgrade(
    revision: str = typer.Argument(..., help="Alembic revision target."),
) -> None:
    """Revert Alembic migrations down to the target revision."""
    project_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        ["uv", "run", "alembic", "downgrade", revision],
        cwd=project_root,
        check=False,
    )
    sys.exit(result.returncode)


@app.command()
def revision(
    message: str = typer.Option(..., "-m", "--message", help="Migration message."),
    autogenerate: bool = typer.Option(True, help="Autogenerate from ORM diff."),
) -> None:
    """Create a new Alembic revision."""
    project_root = Path(__file__).resolve().parents[3]
    cmd = ["uv", "run", "alembic", "revision", "-m", message]
    if autogenerate:
        cmd.append("--autogenerate")
    result = subprocess.run(cmd, cwd=project_root, check=False)
    sys.exit(result.returncode)
