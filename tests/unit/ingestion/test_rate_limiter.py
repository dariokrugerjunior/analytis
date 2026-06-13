"""Tests for the token bucket rate limiter."""

import asyncio
import time

import pytest

from analytis.ingestion.rate_limiter import TokenBucket


@pytest.mark.asyncio
async def test_bucket_allows_burst() -> None:
    bucket = TokenBucket(rate_per_second=10.0, capacity=5)
    start = time.monotonic()
    for _ in range(5):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.05


@pytest.mark.asyncio
async def test_bucket_throttles_after_burst() -> None:
    bucket = TokenBucket(rate_per_second=10.0, capacity=2)
    await bucket.acquire()
    await bucket.acquire()
    start = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.08, f"expected >=80ms, got {elapsed * 1000:.0f}ms"


@pytest.mark.asyncio
async def test_bucket_recovers() -> None:
    bucket = TokenBucket(rate_per_second=100.0, capacity=1)
    await bucket.acquire()
    await asyncio.sleep(0.05)
    start = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.02
