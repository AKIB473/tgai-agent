"""
agent_manager/manager.py — Lifecycle management for sub-agents.
"""

from __future__ import annotations

from typing import Dict, Optional

from tgai_agent.agent_manager.agent import SubAgent
from tgai_agent.storage.repositories.agent_repo import (
    create_agent,
    delete_agent,
    get_agent,
    list_agents,
    update_agent_state,
)
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

# In-memory registry of live agent instances
_live_agents: dict[str, SubAgent] = {}


async def spawn_agent(
    user_id: int,
    name: str,
    role: str,
    system_prompt: str,
    ai_provider: str = "openai",
    ai_model: str = "gpt-4o-mini",
) -> SubAgent:
    """Create and register a new sub-agent."""
    agent_id = await create_agent(
        user_id=user_id,
        name=name,
        role=role,
        system_prompt=system_prompt,
        ai_provider=ai_provider,
        ai_model=ai_model,
    )
    agent = SubAgent(
        agent_id=agent_id,
        user_id=user_id,
        name=name,
        role=role,
        system_prompt=system_prompt,
        ai_provider=ai_provider,
        ai_model=ai_model,
    )
    _live_agents[agent_id] = agent
    log.info("agent.spawned", agent_id=agent_id, name=name, role=role)
    return agent


async def get_live_agent(agent_id: str) -> SubAgent | None:
    """Get a live agent instance, loading from DB if not in memory."""
    if agent_id in _live_agents:
        return _live_agents[agent_id]

    # Try to reload from DB
    data = await get_agent(agent_id)
    if not data:
        return None

    agent = SubAgent(
        agent_id=data["id"],
        user_id=data["user_id"],
        name=data["name"],
        role=data["role"],
        system_prompt=data["system_prompt"],
        ai_provider=data["ai_provider"],
        ai_model=data["ai_model"],
    )
    agent.state = data["state"]
    _live_agents[agent_id] = agent
    return agent


async def list_user_agents(user_id: int) -> list[dict]:
    """Return all agents for a user (from DB)."""
    return await list_agents(user_id)


async def stop_agent(agent_id: str, user_id: int) -> bool:
    """Stop and remove an agent."""
    agent = await get_live_agent(agent_id)
    if agent and agent.user_id == user_id:
        await agent.stop()
        _live_agents.pop(agent_id, None)

    return await delete_agent(agent_id, user_id)


async def talk_to_agent(agent_id: str, user_id: int, message: str) -> str:
    """Send a message to a specific agent and get a response."""
    agent = await get_live_agent(agent_id)
    if not agent:
        return "Agent not found."
    if agent.user_id != user_id:
        return "You don't have permission to talk to this agent."
    return await agent.think(message)
