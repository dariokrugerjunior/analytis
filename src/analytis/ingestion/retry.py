"""Retry helper for transient HTTP errors."""

from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

T = TypeVar("T")

TRANSIENT_EXCEPTIONS = (
    httpx.ConnectTimeout,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
) -> Callable[
    [Callable[..., Coroutine[Any, Any, T]]],
    Callable[..., Coroutine[Any, Any, T]],
]:
    """Decorate an async fn to retry on transient HTTP errors with jittered backoff."""

    def decorator(
        fn: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            retrying = AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential_jitter(initial=base_delay, max=max_delay),
                retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
                reraise=True,
            )
            async for attempt in retrying:
                with attempt:
                    return await fn(*args, **kwargs)
            raise RuntimeError("unreachable")

        return wrapper

    return decorator
