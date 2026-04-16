"""
storage/repositories/chat_repo.py — Per-chat AI configuration.
"""

from __future__ import annotations

from typing import Optional

from tgai_agent.storage.database import get_db
from tgai_agent.storage.encryption import decrypt, encrypt
from tgai_agent.utils.helpers import utcnow
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

# ── API Keys ─────────────────────────────────────────────────────────────────

async def save_api_key(user_id: int, provider: str, api_key: str) -> None:
    now = utcnow().isoformat()
    encrypted = encrypt(api_key)
    async with await get_db() as db:
        await db.execute(
            """
            INSERT INTO api_keys (user_id, provider, key_encrypted, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, provider) DO UPDATE SET
                key_encrypted = excluded.key_encrypted,
                updated_at    = excluded.updated_at
            """,
            (user_id, provider, encrypted, now, now),
        )
        await db.commit()


async def get_api_key(user_id: int, provider: str) -> str:
    """Return the decrypted API key, or empty string if not set."""
    async with await get_db() as db:
        async with db.execute(
            "SELECT key_encrypted FROM api_keys WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        ) as cursor:
            row = await cursor.fetchone()
            return decrypt(row["key_encrypted"]) if row else ""


# ── Chat Config ───────────────────────────────────────────────────────────────

DEFAULT_CHAT_CONFIG = {
    "ai_provider": "openai",
    "ai_model": "gpt-4o-mini",
    "system_prompt": "You are a helpful AI assistant.",
    "auto_reply": False,
    "reply_confirmed": False,
    "tone": "neutral",
    "language": "en",
}


async def get_chat_config(user_id: int, chat_id: int) -> dict:
    async with await get_db() as db:
        async with db.execute(
            "SELECT * FROM chat_configs WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {**DEFAULT_CHAT_CONFIG, "user_id": user_id, "chat_id": chat_id}


async def upsert_chat_config(user_id: int, chat_id: int, **kwargs) -> None:
    now = utcnow().isoformat()
    existing = await get_chat_config(user_id, chat_id)

    # Merge updates onto existing config
    merged = {**existing, **kwargs, "updated_at": now}

    async with await get_db() as db:
        await db.execute(
            """
            INSERT INTO chat_configs
                (user_id, chat_id, chat_title, ai_provider, ai_model,
                 system_prompt, auto_reply, reply_confirmed, tone, language,
                 created_at, updated_at)
            VALUES
                (:user_id, :chat_id, :chat_title, :ai_provider, :ai_model,
                 :system_prompt, :auto_reply, :reply_confirmed, :tone, :language,
                 :created_at, :updated_at)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                chat_title     = excluded.chat_title,
                ai_provider    = excluded.ai_provider,
                ai_model       = excluded.ai_model,
                system_prompt  = excluded.system_prompt,
                auto_reply     = excluded.auto_reply,
                reply_confirmed= excluded.reply_confirmed,
                tone           = excluded.tone,
                language       = excluded.language,
                updated_at     = excluded.updated_at
            """,
            {
                **merged,
                "created_at": merged.get("created_at", now),
                "chat_title": merged.get("chat_title"),
            },
        )
        await db.commit()


# ── Message History ───────────────────────────────────────────────────────────

async def append_message(
    user_id: int,
    chat_id: int,
    role: str,
    content: str,
    token_count: int = 0,
) -> None:
    now = utcnow().isoformat()
    async with await get_db() as db:
        await db.execute(
            """
            INSERT INTO messages (user_id, chat_id, role, content, token_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, chat_id, role, content, token_count, now),
        )
        await db.commit()


async def get_messages(
    user_id: int,
    chat_id: int,
    limit: int = 50,
) -> list[dict]:
    """Return recent messages in chronological order (oldest first)."""
    async with await get_db() as db:
        async with db.execute(
            """
            SELECT role, content FROM messages
            WHERE user_id = ? AND chat_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, chat_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in reversed(rows)]


async def clear_messages(user_id: int, chat_id: int) -> int:
    async with await get_db() as db:
        cursor = await db.execute(
            "DELETE FROM messages WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        )
        await db.commit()
        return cursor.rowcount
