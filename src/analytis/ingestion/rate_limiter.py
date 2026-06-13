"""Token bucket rate limiter for ingestion adapters."""

import asyncio
import time


class TokenBucket:
    """Asyncio-friendly token bucket.

    rate_per_second: tokens refilled per second.
    capacity: max tokens that can accumulate.
    """

    def __init__(self, rate_per_second: float, capacity: int) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._rate = rate_per_second
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
                self._last_refill = now
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                missing = tokens - self._tokens
                wait_s = missing / self._rate
                await asyncio.sleep(wait_s)
