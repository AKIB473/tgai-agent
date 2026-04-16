"""
utils/retry.py — Reusable async retry decorator built on tenacity.

Usage:
    @async_retry(max_attempts=3, wait_seconds=2)
    async def flaky_call():
        ...
"""

from __future__ import annotations

import asyncio
import functools
from typing import Callable, Tuple, Type

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
import logging

from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


def async_retry(
    max_attempts: int = 3,
    wait_seconds: float = 1.0,
    wait_max: float = 30.0,
    reraise: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator that retries an async function with exponential back-off.

    Args:
        max_attempts:  Maximum total attempts (including first try).
        wait_seconds:  Initial wait between retries (doubles each time).
        wait_max:      Maximum wait cap in seconds.
        reraise:       If True, re-raise the last exception after exhausting retries.
        exceptions:    Tuple of exception types to catch and retry on.
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            attempt = 0
            delay = wait_seconds
            last_exc: Exception | None = None

            while attempt < max_attempts:
                try:
                    return await fn(*args, **kwargs)
                except exceptions as exc:
                    attempt += 1
                    last_exc = exc
                    if attempt >= max_attempts:
                        break
                    sleep_for = min(delay * (2 ** (attempt - 1)), wait_max)
                    log.warning(
                        "retry.sleeping",
                        fn=fn.__qualname__,
                        attempt=attempt,
                        max=max_attempts,
                        sleep=sleep_for,
                        error=str(exc),
                    )
                    await asyncio.sleep(sleep_for)

            log.error(
                "retry.exhausted",
                fn=fn.__qualname__,
                attempts=max_attempts,
                error=str(last_exc),
            )
            if reraise and last_exc:
                raise last_exc

        return wrapper

    return decorator
