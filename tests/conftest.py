"""
tests/conftest.py — Shared pytest fixtures.
"""

from __future__ import annotations

import os
import pytest
import pytest_asyncio
import aiosqlite

# Force test environment before any imports
os.environ.setdefault("BOT_TOKEN", "1234567890:test_token_for_pytest_only")
os.environ.setdefault("API_ID", "12345678")
os.environ.setdefault("API_HASH", "testhashvalue")
os.environ.setdefault("ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ=")
os.environ.setdefault("ADMIN_IDS", "999999")
os.environ.setdefault("DB_PATH", ":memory:")
os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite database with schema applied."""
    from tgai_agent.storage.database import SCHEMA_SQL
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.executescript(SCHEMA_SQL)
    await conn.commit()
    yield conn
    await conn.close()


@pytest.fixture
def sample_user_id() -> int:
    return 123456789


@pytest.fixture
def sample_chat_id() -> int:
    return -100123456789
