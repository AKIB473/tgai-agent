"""
storage/repositories/task_repo.py — Scheduled task persistence.
"""

from __future__ import annotations

import json
import uuid
from typing import Optional

from tgai_agent.storage.database import get_db
from tgai_agent.utils.helpers import utcnow
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


async def create_task(
    user_id: int,
    name: str,
    trigger_type: str,
    trigger_value: str,
    action_type: str,
    action_payload: dict,
    description: str = "",
    next_run_at: str | None = None,
) -> str:
    task_id = str(uuid.uuid4())
    now = utcnow().isoformat()
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO tasks
                (id, user_id, name, description, trigger_type, trigger_value,
                 action_type, action_payload, is_active, next_run_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                task_id,
                user_id,
                name,
                description,
                trigger_type,
                trigger_value,
                action_type,
                json.dumps(action_payload),
                next_run_at,
                now,
            ),
        )
        await db.commit()
    log.info("task.created", task_id=task_id, name=name)
    return task_id


async def get_task(task_id: str) -> dict | None:
    async with get_db() as db:
        async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["action_payload"] = json.loads(d["action_payload"])
            return d


async def list_tasks(user_id: int, active_only: bool = True) -> list[dict]:
    query = "SELECT * FROM tasks WHERE user_id = ?"
    params: list = [user_id]
    if active_only:
        query += " AND is_active = 1"
    query += " ORDER BY created_at DESC"

    async with get_db() as db, db.execute(query, params) as cursor:
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["action_payload"] = json.loads(d["action_payload"])
            result.append(d)
        return result


async def update_task_run(task_id: str, next_run_at: str | None = None) -> None:
    now = utcnow().isoformat()
    async with get_db() as db:
        await db.execute(
            """
            UPDATE tasks
            SET last_run_at = ?, next_run_at = ?, run_count = run_count + 1
            WHERE id = ?
            """,
            (now, next_run_at, task_id),
        )
        await db.commit()


async def deactivate_task(task_id: str) -> None:
    async with get_db() as db:
        await db.execute("UPDATE tasks SET is_active = 0 WHERE id = ?", (task_id,))
        await db.commit()


async def delete_task(task_id: str, user_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0
