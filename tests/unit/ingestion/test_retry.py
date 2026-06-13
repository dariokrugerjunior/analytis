"""Tests for the retry helper."""

import httpx
import pytest

from analytis.ingestion.retry import with_retry


class _Counter:
    def __init__(self) -> None:
        self.calls = 0


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failures() -> None:
    counter = _Counter()

    @with_retry(max_attempts=3, base_delay=0.01)
    async def flaky() -> str:
        counter.calls += 1
        if counter.calls < 3:
            raise httpx.ConnectTimeout("boom")
        return "ok"

    result = await flaky()
    assert result == "ok"
    assert counter.calls == 3


@pytest.mark.asyncio
async def test_retry_gives_up_after_max() -> None:
    counter = _Counter()

    @with_retry(max_attempts=2, base_delay=0.01)
    async def always_fails() -> str:
        counter.calls += 1
        raise httpx.ConnectTimeout("boom")

    with pytest.raises(httpx.ConnectTimeout):
        await always_fails()
    assert counter.calls == 2


@pytest.mark.asyncio
async def test_retry_does_not_retry_on_non_transient() -> None:
    counter = _Counter()

    @with_retry(max_attempts=3, base_delay=0.01)
    async def bad_input() -> str:
        counter.calls += 1
        raise ValueError("permanent")

    with pytest.raises(ValueError, match="permanent"):
        await bad_input()
    assert counter.calls == 1
