"""Tests for the sliding-window rate limiter."""

import pytest

from tgai_agent.security import rate_guard


@pytest.mark.asyncio
async def test_first_request_allowed():
    # Fresh user should be allowed
    assert await rate_guard.check_user_rate_limit(88888) is True


@pytest.mark.asyncio
async def test_rate_limit_exceeded(monkeypatch):
    import time

    uid = 77777
    # Fill the window to the limit
    monkeypatch.setattr(rate_guard, "_request_windows", {})
    from collections import deque

    now = time.monotonic()
    # Simulate window full
    rate_guard._request_windows[uid] = deque([now] * rate_guard.settings.max_requests_per_minute)
    assert await rate_guard.check_user_rate_limit(uid) is False


@pytest.mark.asyncio
async def test_combined_check_passes_new_user():
    result = await rate_guard.is_rate_limited(55555, chat_id=-100999)
    assert result is False
