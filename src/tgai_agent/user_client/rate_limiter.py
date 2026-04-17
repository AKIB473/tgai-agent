"""
user_client/rate_limiter.py — Telethon flood-wait handler and anti-spam logic.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque

from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

# Per-peer (chat) send windows to prevent flood
_send_windows: dict[int, deque] = defaultdict(deque)
MAX_SENDS_PER_MINUTE_PER_PEER = 3


async def handle_flood_wait(exc) -> None:
    """
    When Telethon raises FloodWaitError, sleep for the required duration.
    Called by event listeners automatically.
    """
    wait_seconds = getattr(exc, "seconds", 30)
    log.warning("telethon.flood_wait", seconds=wait_seconds)
    await asyncio.sleep(wait_seconds + 1)  # +1 buffer


async def can_send_to_peer(peer_id: int) -> bool:
    """
    Conservative rate check: max 3 automated messages per peer per minute.
    Returns True if we may send.
    """
    import time

    now = time.monotonic()
    window = _send_windows[peer_id]
    while window and window[0] < now - 60:
        window.popleft()
    if len(window) >= MAX_SENDS_PER_MINUTE_PER_PEER:
        log.warning("telethon.peer_rate_limited", peer_id=peer_id)
        return False
    window.append(now)
    return True
