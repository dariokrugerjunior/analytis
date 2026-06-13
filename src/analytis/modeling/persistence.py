"""Persistence helpers for fitted Dixon-Coles models.

Models are serialised via pickle into `./models/<version_id>.pkl`.
The ORM `model_version` row stores hyperparams, metrics, git SHA, and the
artifact path.
"""

import pickle
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import UUID

from analytis.modeling.fitting import DixonColesParams

DEFAULT_MODELS_DIR = Path("models")


def save_params(
    params: DixonColesParams,
    version_id: UUID,
    *,
    models_dir: Path | None = None,
) -> Path:
    target_dir = models_dir or DEFAULT_MODELS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{version_id}.pkl"
    with target_path.open("wb") as fh:
        pickle.dump(asdict(params), fh)
    return target_path


def load_params(path: Path) -> DixonColesParams:
    with path.open("rb") as fh:
        data: dict[str, Any] = pickle.load(fh)
    return DixonColesParams(
        attack=dict(data["attack"]),
        defense=dict(data["defense"]),
        home_advantage=float(data["home_advantage"]),
        rho=float(data["rho"]),
    )


__all__ = ["DEFAULT_MODELS_DIR", "load_params", "save_params"]
