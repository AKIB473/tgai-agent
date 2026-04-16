"""
agent_manager/agent.py — Sub-agent base class.

Each sub-agent has:
  - An identity (name, role, system prompt)
  - Its own AI provider + memory
  - A state machine (idle → running → stopped)
  - The ability to use plugins as tools
"""

from __future__ import annotations

import asyncio
from typing import Any

from tgai_agent.ai_core.base_provider import AIMessage
from tgai_agent.ai_core.memory.short_term import ShortTermMemory
from tgai_agent.ai_core.router import complete
from tgai_agent.plugins.registry import PluginRegistry
from tgai_agent.storage.repositories.agent_repo import update_agent_memory, update_agent_state
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


class AgentState:
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"


class SubAgent:
    """
    A lightweight autonomous agent with its own identity and memory.
    Can be created per-task (e.g. "research agent", "email drafter").
    """

    def __init__(
        self,
        agent_id: str,
        user_id: int,
        name: str,
        role: str,
        system_prompt: str,
        ai_provider: str,
        ai_model: str,
    ) -> None:
        self.agent_id = agent_id
        self.user_id = user_id
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.ai_provider = ai_provider
        self.ai_model = ai_model
        self.state = AgentState.IDLE

        # Use chat_id = -1 as a namespace for this agent's personal memory
        self._memory = ShortTermMemory(user_id, chat_id=-int(agent_id[:8], 16) % (2**31))
        self._task: asyncio.Task | None = None

    async def think(self, user_message: str) -> str:
        """
        Process a message and return a response.
        Adds both the user message and response to the agent's memory.
        """
        await self._memory.add("user", user_message)

        messages = await self._memory.get_context(system_prompt=self.system_prompt)

        try:
            response = await complete(
                self.user_id,
                self.ai_provider,
                messages,
                model=self.ai_model,
            )
        except Exception as exc:
            log.error("agent.think_failed", agent=self.name, error=str(exc))
            response = f"[Agent error: {exc}]"

        await self._memory.add("assistant", response)
        await update_agent_memory(self.agent_id, [])  # persist memory snapshot
        return response

    async def run_task(self, task_description: str, context: dict) -> str:
        """
        Run a multi-step task autonomously.
        The agent may call plugins as tools to complete the task.
        """
        if self.state == AgentState.RUNNING:
            return "Agent is already running a task."

        self.state = AgentState.RUNNING
        await update_agent_state(self.agent_id, AgentState.RUNNING)

        try:
            # Build task prompt with available tool descriptions
            available_tools = "\n".join(
                f"- {p.name}: {p.description}"
                for p in PluginRegistry.list_all()
            )
            task_prompt = (
                f"Your task: {task_description}\n\n"
                f"Available tools:\n{available_tools}\n\n"
                "To use a tool, respond with:\n"
                "TOOL: <tool_name>\nPARAMS: <json_params>\n\n"
                "When done, respond with:\nRESULT: <final answer>"
            )

            response = await self.think(task_prompt)

            # Simple tool-call parsing loop (max 5 iterations)
            for _ in range(5):
                if "TOOL:" not in response:
                    break
                tool_result = await self._handle_tool_call(response, context)
                response = await self.think(f"Tool result: {tool_result}\nContinue the task.")

            return response
        finally:
            self.state = AgentState.IDLE
            await update_agent_state(self.agent_id, AgentState.IDLE)

    async def _handle_tool_call(self, response: str, context: dict) -> str:
        """Parse and execute a tool call from the agent's response."""
        import json, re
        tool_match = re.search(r"TOOL:\s*(\w+)", response)
        params_match = re.search(r"PARAMS:\s*(\{.*?\})", response, re.DOTALL)

        if not tool_match:
            return "Could not parse tool call."

        tool_name = tool_match.group(1)
        try:
            params = json.loads(params_match.group(1)) if params_match else {}
        except json.JSONDecodeError:
            params = {}

        try:
            return await PluginRegistry.run(tool_name, params, context)
        except Exception as exc:
            return f"Tool error: {exc}"

    async def stop(self) -> None:
        self.state = AgentState.STOPPED
        await update_agent_state(self.agent_id, AgentState.STOPPED)
        if self._task and not self._task.done():
            self._task.cancel()

    def __repr__(self) -> str:
        return f"SubAgent(name={self.name!r}, role={self.role!r}, state={self.state})"
