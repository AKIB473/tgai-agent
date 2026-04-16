"""
storage/repositories/user_repo.py — CRUD for the `users` table.
"""

from __future__ import annotations

from typing import Optional

from tgai_agent.storage.database import get_db
from tgai_agent.utils.helpers import utcnow
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


async def upsert_user(
    user_id: int,
    username: str | None = None,
    first_name: str | None = None,
    is_admin: bool = False,
) -> None:
    now = utcnow().isoformat()
    async with await get_db() as db:
        await db.execute(
            """
            INSERT INTO users (id, username, first_name, is_admin, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                updated_at = excluded.updated_at
            """,
            (user_id, username, first_name, int(is_admin), now, now),
        )
        await db.commit()


async def get_user(user_id: int) -> Optional[dict]:
    async with await get_db() as db:
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def is_banned(user_id: int) -> bool:
    user = await get_user(user_id)
    return bool(user and user["is_banned"])


async def ban_user(user_id: int) -> None:
    now = utcnow().isoformat()
    async with await get_db() as db:
        await db.execute(
            "UPDATE users SET is_banned = 1, updated_at = ? WHERE id = ?",
            (now, user_id),
        )
        await db.commit()


async def list_users(limit: int = 100) -> list[dict]:
    async with await get_db() as db:
        async with db.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]
