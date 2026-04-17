"""
utils/helpers.py — Miscellaneous helper functions.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timezone
from typing import Any


def utcnow() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(tz=UTC)


def truncate(text: str, max_len: int = 4000) -> str:
    """Truncate text to max_len, appending ellipsis if cut."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def sanitise_markdown(text: str) -> str:
    """Escape Telegram MarkdownV2 special characters."""
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


def hash_user_id(user_id: int) -> str:
    """One-way hash of a Telegram user ID (for anonymous logging)."""
    return hashlib.sha256(str(user_id).encode()).hexdigest()[:12]


def chunk_list(lst: list, size: int) -> list[list]:
    """Split a list into chunks of at most `size` items."""
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def flatten(nested: list[list[Any]]) -> list[Any]:
    """Flatten one level of nesting."""
    return [item for sub in nested for item in sub]


def parse_duration(text: str) -> int:
    """
    Parse a human duration string into seconds.
    Examples: "5m", "2h", "1d", "30s" → int seconds.
    Raises ValueError on unrecognised format.
    """
    pattern = re.compile(r"^(\d+)(s|m|h|d)$", re.IGNORECASE)
    m = pattern.match(text.strip())
    if not m:
        raise ValueError(f"Cannot parse duration: {text!r}. Use format: 30s, 5m, 2h, 1d")
    value, unit = int(m.group(1)), m.group(2).lower()
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return value * multipliers[unit]
