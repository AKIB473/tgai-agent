"""
storage/repositories/agent_repo.py — Sub-agent persistence.
"""

from __future__ import annotations

import json
import uuid

from tgai_agent.storage.database import get_db
from tgai_agent.utils.helpers import utcnow
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


async def create_agent(
    user_id: int,
    name: str,
    role: str,
    system_prompt: str,
    ai_provider: str,
    ai_model: str,
) -> str:
    agent_id = str(uuid.uuid4())
    now = utcnow().isoformat()
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO agents
                (id, user_id, name, role, system_prompt, ai_provider, ai_model,
                 state, memory_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'idle', '[]', ?, ?)
            """,
            (agent_id, user_id, name, role, system_prompt, ai_provider, ai_model, now, now),
        )
        await db.commit()
    return agent_id


async def get_agent(agent_id: str) -> dict | None:
    async with get_db() as db:
        async with db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["memory_json"] = json.loads(d["memory_json"])
            return d


async def list_agents(user_id: int) -> list[dict]:
    async with (
        get_db() as db,
        db.execute(
            "SELECT * FROM agents WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ) as cursor,
    ):
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["memory_json"] = json.loads(d["memory_json"])
            result.append(d)
        return result


async def update_agent_state(agent_id: str, state: str) -> None:
    now = utcnow().isoformat()
    async with get_db() as db:
        await db.execute(
            "UPDATE agents SET state = ?, updated_at = ? WHERE id = ?",
            (state, now, agent_id),
        )
        await db.commit()


async def update_agent_memory(agent_id: str, memory: list[dict]) -> None:
    now = utcnow().isoformat()
    async with get_db() as db:
        await db.execute(
            "UPDATE agents SET memory_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(memory), now, agent_id),
        )
        await db.commit()


async def delete_agent(agent_id: str, user_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM agents WHERE id = ? AND user_id = ?",
            (agent_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0
