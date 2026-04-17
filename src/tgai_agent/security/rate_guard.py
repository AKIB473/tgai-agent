"""
security/rate_guard.py — In-memory per-user rate limiting.

Uses a sliding-window token bucket to prevent:
  - API abuse
  - Accidental message floods
  - Spam from compromised accounts
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from tgai_agent.config import settings
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

# Global storage: user_id → deque of timestamps
_request_windows: dict[int, deque[float]] = defaultdict(deque)
_chat_windows: dict[tuple, deque[float]] = defaultdict(deque)

_lock = asyncio.Lock()


def _clean_window(window: deque[float], now: float, period: float) -> None:
    """Remove timestamps older than `period` seconds."""
    while window and window[0] < now - period:
        window.popleft()


async def check_user_rate_limit(user_id: int) -> bool:
    """
    Check global request rate for a user.
    Returns True if allowed, False if rate limited.
    """
    now = time.monotonic()
    limit = settings.max_requests_per_minute

    async with _lock:
        window = _request_windows[user_id]
        _clean_window(window, now, 60.0)

        if len(window) >= limit:
            log.warning(
                "rate_guard.user_limited",
                user_id=user_id,
                count=len(window),
                limit=limit,
            )
            return False

        window.append(now)
        return True


async def check_chat_rate_limit(user_id: int, chat_id: int) -> bool:
    """
    Check per-chat message rate for a user.
    Returns True if allowed, False if rate limited.
    """
    now = time.monotonic()
    limit = settings.max_messages_per_chat_per_minute
    key = (user_id, chat_id)

    async with _lock:
        window = _chat_windows[key]
        _clean_window(window, now, 60.0)

        if len(window) >= limit:
            log.warning(
                "rate_guard.chat_limited",
                user_id=user_id,
                chat_id=chat_id,
                count=len(window),
                limit=limit,
            )
            return False

        window.append(now)
        return True


async def is_rate_limited(user_id: int, chat_id: int | None = None) -> bool:
    """Combined check: user-global + optional per-chat."""
    if not await check_user_rate_limit(user_id):
        return True
    if chat_id is not None and not await check_chat_rate_limit(user_id, chat_id):
        return True
    return False
