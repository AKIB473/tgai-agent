"""
agent_manager/agent.py — Sub-agent with improved ReAct loop and tool calling.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from tgai_agent.ai_core.base_provider import AIMessage
from tgai_agent.ai_core.memory.short_term import ShortTermMemory
from tgai_agent.ai_core.router import complete
from tgai_agent.plugins.registry import PluginRegistry
from tgai_agent.storage.repositories.agent_repo import update_agent_memory, update_agent_state
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

MAX_TOOL_ITERATIONS = 10


class AgentState:
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"


class SubAgent:
    """
    A lightweight autonomous agent with its own identity and memory.
    Supports multi-turn conversations and tool use via ReAct loop.
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
        self.last_active: str | None = None

        # Use a stable negative chat_id derived from agent UUID
        import hashlib

        hash_val = int(hashlib.md5(agent_id.encode()).hexdigest()[:8], 16)
        self._chat_id = -(hash_val % (2**30))
        self._memory = ShortTermMemory(user_id, chat_id=self._chat_id)
        self._task: asyncio.Task | None = None

    async def think(self, user_message: str) -> str:
        """
        Process a message and return a response.
        Adds both the user message and response to the agent's memory.
        """
        from tgai_agent.utils.helpers import utcnow

        self.last_active = utcnow().isoformat()

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
            response = f"⚠️ Agent error: {exc}"

        await self._memory.add("assistant", response)
        await update_agent_memory(self.agent_id, [])
        return response

    async def run_task(self, task_description: str, context: dict) -> str:
        """
        Run a multi-step task autonomously using a ReAct loop.
        The agent may call plugins as tools to complete the task.
        """
        if self.state == AgentState.RUNNING:
            return "⚠️ Agent is already running a task. Please wait."

        self.state = AgentState.RUNNING
        await update_agent_state(self.agent_id, AgentState.RUNNING)

        try:
            return await self._react_loop(task_description, context)
        except Exception as exc:
            log.error("agent.run_task_failed", agent=self.name, error=str(exc))
            return f"⚠️ Task failed: {exc}"
        finally:
            self.state = AgentState.IDLE
            await update_agent_state(self.agent_id, AgentState.IDLE)

    async def _react_loop(self, task_description: str, context: dict) -> str:
        """
        ReAct (Reason + Act) loop:
        1. Show the agent the task + available tools
        2. Agent responds with reasoning + optional tool call
        3. Execute tool, inject result, repeat
        4. Stop when agent outputs RESULT: or max iterations reached
        """
        plugins = PluginRegistry.list_all()
        tool_descriptions = "\n".join(f"- **{p.name}**: {p.description}" for p in plugins)

        system_with_tools = (
            f"{self.system_prompt}\n\n"
            f"## Available Tools\n{tool_descriptions}\n\n"
            "## Tool Usage Format\n"
            "To call a tool, write:\n"
            "TOOL: <tool_name>\n"
            'PARAMS: {"key": "value"}\n\n'
            "When you have your final answer, write:\n"
            "RESULT: <your final answer>"
        )

        await self._memory.add("user", f"Task: {task_description}")
        messages = await self._memory.get_context(system_prompt=system_with_tools)

        response = await complete(self.user_id, self.ai_provider, messages, model=self.ai_model)

        for iteration in range(MAX_TOOL_ITERATIONS):
            # Check if done
            result_match = re.search(r"RESULT:\s*(.+)", response, re.DOTALL)
            if result_match:
                final = result_match.group(1).strip()
                await self._memory.add("assistant", response)
                return final

            # Check for tool call
            tool_match = re.search(r"TOOL:\s*(\w+)", response)
            params_match = re.search(r"PARAMS:\s*(\{.*?\})", response, re.DOTALL)

            if not tool_match:
                # No tool call, no RESULT — treat as final answer
                await self._memory.add("assistant", response)
                return response

            tool_name = tool_match.group(1).strip()
            try:
                params = json.loads(params_match.group(1)) if params_match else {}
            except json.JSONDecodeError:
                params = {}

            # Execute tool
            log.info("agent.tool_call", agent=self.name, tool=tool_name, params=params)
            try:
                tool_result = await PluginRegistry.run(
                    tool_name,
                    params,
                    {
                        **context,
                        "user_id": self.user_id,
                    },
                )
            except Exception as exc:
                tool_result = f"Tool error: {exc}"

            # Inject result and continue
            await self._memory.add("assistant", response)
            await self._memory.add(
                "user",
                f"Tool result for {tool_name}:\n{tool_result}\n\nContinue the task.",
            )
            messages = await self._memory.get_context(system_prompt=system_with_tools)
            response = await complete(self.user_id, self.ai_provider, messages, model=self.ai_model)

        # Max iterations reached
        await self._memory.add("assistant", response)
        return f"{response}\n\n_(Max tool iterations reached)_"

    async def clear_memory(self) -> int:
        """Clear this agent's conversation memory."""
        return await self._memory.clear()

    async def memory_summary(self) -> str:
        """Return memory summary string."""
        return await self._memory.summary()

    async def stop(self) -> None:
        self.state = AgentState.STOPPED
        await update_agent_state(self.agent_id, AgentState.STOPPED)
        if self._task and not self._task.done():
            self._task.cancel()

    def __repr__(self) -> str:
        return f"SubAgent(name={self.name!r}, role={self.role!r}, state={self.state})"
