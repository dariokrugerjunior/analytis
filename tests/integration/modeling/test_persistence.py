"""Integration test for model save/load + ModelVersion repo."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.modeling.fitting import DixonColesParams
from analytis.modeling.persistence import load_params, save_params
from analytis.persistence.repositories import ModelVersionRepository
from analytis.persistence.unit_of_work import UnitOfWork


def test_save_load_roundtrip(tmp_path: Path) -> None:
    params = DixonColesParams(
        attack={"A": 0.2, "B": -0.1},
        defense={"A": -0.05, "B": 0.1},
        home_advantage=0.3,
        rho=-0.04,
    )
    version_id = uuid4()
    path = save_params(params, version_id, models_dir=tmp_path)
    assert path.exists()

    loaded = load_params(path)
    assert loaded.attack == params.attack
    assert loaded.defense == params.defense
    assert loaded.home_advantage == params.home_advantage
    assert loaded.rho == params.rho


@pytest.mark.integration
async def test_model_version_insert_and_get(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with UnitOfWork(session_factory) as uow:
        repo = ModelVersionRepository(uow.session)
        vid = await repo.insert(
            name="dixon-coles-test-v0.0.1",
            family="dixon-coles",
            git_sha="abc1234",
            hyperparams={"decay_per_day": 0.005, "sigma": 0.3},
            metrics={"brier_1x2": 0.21},
            artifact_path="models/test.pkl",
            trained_at=datetime(2026, 6, 13, tzinfo=UTC),
        )

    async with session_factory() as s:
        repo = ModelVersionRepository(s)
        orm = await repo.get(vid)
        assert orm is not None
        assert orm.name == "dixon-coles-test-v0.0.1"
        assert orm.hyperparams["decay_per_day"] == 0.005
        assert orm.metrics["brier_1x2"] == 0.21
        assert orm.is_promoted is False

        by_name = await repo.get_by_name("dixon-coles-test-v0.0.1")
        assert by_name is not None
        assert by_name.id == vid
