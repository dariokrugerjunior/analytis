"""Tests for the feature registry."""

import pytest

from analytis.features.registry import FeatureRegistry


@pytest.mark.asyncio
async def test_registry_register_and_compute() -> None:
    reg = FeatureRegistry()

    @reg.register("constant_one")
    async def _const(_ctx: object) -> float:
        return 1.0

    @reg.register("constant_two")
    async def _two(_ctx: object) -> float:
        return 2.0

    out = await reg.compute_all(context=None)
    assert out == {"constant_one": 1.0, "constant_two": 2.0}


def test_registry_rejects_duplicate_name() -> None:
    reg = FeatureRegistry()

    @reg.register("dup")
    async def _a(_ctx: object) -> float:
        return 0.0

    with pytest.raises(ValueError, match="already registered"):

        @reg.register("dup")
        async def _b(_ctx: object) -> float:
            return 1.0
