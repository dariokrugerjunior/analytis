"""CLI commands for the React frontend."""

import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Frontend (Vite + React) operations.")
console = Console()


def _frontend_dir() -> Path:
    root = Path(__file__).resolve().parents[3]
    target = root / "frontend"
    if not target.exists():
        console.print(f"[red]frontend/ directory not found at {target}[/red]")
        raise typer.Exit(code=2)
    return target


def _pnpm() -> str:
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        console.print("[red]pnpm not found on PATH[/red]")
        console.print("Install with: npm install -g pnpm")
        raise typer.Exit(code=2)
    return pnpm


def _run(cmd: list[str], cwd: Path) -> int:
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    proc = subprocess.run(cmd, cwd=cwd, check=False)
    return proc.returncode


@app.command()
def install() -> None:
    """Install frontend dependencies via pnpm."""
    fe = _frontend_dir()
    code = _run([_pnpm(), "install"], cwd=fe)
    sys.exit(code)


@app.command()
def build() -> None:
    """Type-check and build the frontend (output: frontend/dist/)."""
    fe = _frontend_dir()
    pnpm = _pnpm()
    code = _run([pnpm, "install"], cwd=fe)
    if code != 0:
        sys.exit(code)
    code = _run([pnpm, "build"], cwd=fe)
    sys.exit(code)


@app.command()
def dev() -> None:
    """Run the Vite dev server (proxies /v1 to FastAPI in :8000)."""
    fe = _frontend_dir()
    code = _run([_pnpm(), "dev"], cwd=fe)
    sys.exit(code)
