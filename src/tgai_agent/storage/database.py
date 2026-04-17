"""
storage/database.py — SQLite initialisation, migrations, and connection pool.

All repositories import `get_db()` to obtain an aiosqlite connection.
Schema versioning uses a simple `schema_version` pragma table.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import aiosqlite

from tgai_agent.config import settings
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

# ── Schema definition ────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- Users & their per-user settings
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY,   -- Telegram user ID
    username        TEXT,
    first_name      TEXT,
    is_admin        BOOLEAN DEFAULT 0,
    is_banned       BOOLEAN DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

-- Encrypted API key storage (one row per provider per user)
CREATE TABLE IF NOT EXISTS api_keys (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    provider        TEXT NOT NULL,          -- 'openai' | 'gemini' | 'claude'
    key_encrypted   TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    UNIQUE(user_id, provider)
);

-- Per-chat configuration rules
CREATE TABLE IF NOT EXISTS chat_configs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    chat_id         INTEGER NOT NULL,
    chat_title      TEXT,
    ai_provider     TEXT DEFAULT 'openai',
    ai_model        TEXT DEFAULT 'gpt-4o-mini',
    system_prompt   TEXT DEFAULT '',
    auto_reply      BOOLEAN DEFAULT 0,
    reply_confirmed BOOLEAN DEFAULT 0,       -- user has approved auto-reply for this chat
    tone            TEXT DEFAULT 'neutral',  -- 'formal' | 'casual' | 'neutral'
    language        TEXT DEFAULT 'en',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    UNIQUE(user_id, chat_id)
);

-- Conversation memory (short-term stored persistently)
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    chat_id         INTEGER NOT NULL,
    role            TEXT NOT NULL,           -- 'user' | 'assistant' | 'system'
    content         TEXT NOT NULL,
    token_count     INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(user_id, chat_id, created_at);

-- Scheduled tasks
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,        -- UUID
    user_id         INTEGER NOT NULL REFERENCES users(id),
    name            TEXT NOT NULL,
    description     TEXT,
    trigger_type    TEXT NOT NULL,           -- 'once' | 'interval' | 'cron'
    trigger_value   TEXT NOT NULL,           -- ISO timestamp | seconds | cron expr
    action_type     TEXT NOT NULL,           -- 'message' | 'agent' | 'plugin'
    action_payload  TEXT NOT NULL,           -- JSON
    is_active       BOOLEAN DEFAULT 1,
    last_run_at     TEXT,
    next_run_at     TEXT,
    run_count       INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL
);

-- Sub-agent states
CREATE TABLE IF NOT EXISTS agents (
    id              TEXT PRIMARY KEY,        -- UUID
    user_id         INTEGER NOT NULL REFERENCES users(id),
    name            TEXT NOT NULL,
    role            TEXT NOT NULL,
    system_prompt   TEXT NOT NULL,
    ai_provider     TEXT NOT NULL,
    ai_model        TEXT NOT NULL,
    state           TEXT DEFAULT 'idle',     -- 'idle' | 'running' | 'stopped'
    memory_json     TEXT DEFAULT '[]',       -- serialised short-term memory
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

-- Plugin execution audit log
CREATE TABLE IF NOT EXISTS plugin_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    plugin_name     TEXT NOT NULL,
    params_json     TEXT,
    result_snippet  TEXT,
    duration_ms     INTEGER,
    success         BOOLEAN,
    created_at      TEXT NOT NULL
);
"""


async def init_db() -> None:
    """Create all tables. Safe to call on every startup (IF NOT EXISTS)."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.executescript(SCHEMA_SQL)
        await db.commit()
    log.info("database.initialised", path=settings.db_path)


@asynccontextmanager
async def get_db():
    """
    Async context manager that opens a fresh aiosqlite connection per call.

    Usage (always use as async context manager, never await alone)::

        async with get_db() as db:
            ...

    For backwards compatibility, also supports the legacy pattern::

        async with await get_db() as db:
            ...

    Because asynccontextmanager objects support both await (returning self)
    and async context manager protocol.
    """
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
