"""Feature registry — async function map for batch computation."""

from collections.abc import Awaitable, Callable
from typing import Any

FeatureFn = Callable[[Any], Awaitable[float | None]]


class FeatureRegistry:
    def __init__(self) -> None:
        self._fns: dict[str, FeatureFn] = {}

    def register(self, name: str) -> Callable[[FeatureFn], FeatureFn]:
        def _decorator(fn: FeatureFn) -> FeatureFn:
            if name in self._fns:
                raise ValueError(f"feature {name!r} already registered")
            self._fns[name] = fn
            return fn

        return _decorator

    def names(self) -> list[str]:
        return list(self._fns.keys())

    async def compute_all(self, context: Any) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for name, fn in self._fns.items():
            result[name] = await fn(context)
        return result
