"""
Tests for SubAgent:
- think() adds to memory and returns response
- run_task() parses TOOL: calls and calls plugins
- Agent state changes correctly
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tgai_agent.agent_manager.agent import SubAgent, AgentState


def _make_agent(agent_id: str = "aaaabbbb-0000-0000-0000-000000000001") -> SubAgent:
    """Create a SubAgent with mocked DB dependencies."""
    with (
        patch("tgai_agent.agent_manager.agent.ShortTermMemory"),
        patch("tgai_agent.agent_manager.agent.update_agent_memory", new=AsyncMock()),
        patch("tgai_agent.agent_manager.agent.update_agent_state", new=AsyncMock()),
    ):
        agent = SubAgent(
            agent_id=agent_id,
            user_id=42,
            name="TestAgent",
            role="researcher",
            system_prompt="You are a research assistant.",
            ai_provider="openai",
            ai_model="gpt-4o-mini",
        )
    return agent


class TestSubAgentThink:
    async def test_think_returns_response(self):
        agent = _make_agent()
        mock_memory = MagicMock()
        mock_memory.add = AsyncMock()
        mock_memory.get_context = AsyncMock(return_value=[])
        agent._memory = mock_memory

        with (
            patch(
                "tgai_agent.agent_manager.agent.complete",
                new=AsyncMock(return_value="I found the answer"),
            ),
            patch(
                "tgai_agent.agent_manager.agent.update_agent_memory",
                new=AsyncMock(),
            ),
        ):
            result = await agent.think("What is Python?")

        assert result == "I found the answer"
        assert isinstance(result, str)

    async def test_think_adds_user_message_to_memory(self):
        agent = _make_agent()
        mock_memory = MagicMock()
        mock_memory.add = AsyncMock()
        mock_memory.get_context = AsyncMock(return_value=[])
        agent._memory = mock_memory

        with (
            patch(
                "tgai_agent.agent_manager.agent.complete",
                new=AsyncMock(return_value="response"),
            ),
            patch(
                "tgai_agent.agent_manager.agent.update_agent_memory",
                new=AsyncMock(),
            ),
        ):
            await agent.think("User question here")

        # Should add user message then assistant message
        calls = mock_memory.add.call_args_list
        assert len(calls) == 2
        assert calls[0][0] == ("user", "User question here")
        assert calls[1][0] == ("assistant", "response")

    async def test_think_adds_assistant_response_to_memory(self):
        agent = _make_agent()
        mock_memory = MagicMock()
        mock_memory.add = AsyncMock()
        mock_memory.get_context = AsyncMock(return_value=[])
        agent._memory = mock_memory

        with (
            patch(
                "tgai_agent.agent_manager.agent.complete",
                new=AsyncMock(return_value="AI response"),
            ),
            patch(
                "tgai_agent.agent_manager.agent.update_agent_memory",
                new=AsyncMock(),
            ),
        ):
            result = await agent.think("question")

        assistant_calls = [c for c in mock_memory.add.call_args_list if c[0][0] == "assistant"]
        assert len(assistant_calls) == 1
        assert assistant_calls[0][0][1] == "AI response"

    async def test_think_handles_ai_error(self):
        """When AI call fails, think() returns an error string (not raise)."""
        agent = _make_agent()
        mock_memory = MagicMock()
        mock_memory.add = AsyncMock()
        mock_memory.get_context = AsyncMock(return_value=[])
        agent._memory = mock_memory

        with (
            patch(
                "tgai_agent.agent_manager.agent.complete",
                new=AsyncMock(side_effect=Exception("API down")),
            ),
            patch(
                "tgai_agent.agent_manager.agent.update_agent_memory",
                new=AsyncMock(),
            ),
        ):
            result = await agent.think("question")

        assert "error" in result.lower() or "Agent error" in result

    async def test_think_uses_system_prompt(self):
        agent = _make_agent()
        mock_memory = MagicMock()
        mock_memory.add = AsyncMock()
        mock_memory.get_context = AsyncMock(return_value=[])
        agent._memory = mock_memory

        with (
            patch(
                "tgai_agent.agent_manager.agent.complete",
                new=AsyncMock(return_value="ok"),
            ) as mock_complete,
            patch(
                "tgai_agent.agent_manager.agent.update_agent_memory",
                new=AsyncMock(),
            ),
        ):
            await agent.think("Hello")

        # get_context should be called with system prompt
        mock_memory.get_context.assert_called_once_with(
            system_prompt="You are a research assistant."
        )


class TestSubAgentRunTask:
    async def test_run_task_state_changes_to_running_then_idle(self):
        agent = _make_agent()
        mock_memory = MagicMock()
        mock_memory.add = AsyncMock()
        mock_memory.get_context = AsyncMock(return_value=[])
        agent._memory = mock_memory

        states_recorded = []

        async def mock_update_state(agent_id, state):
            states_recorded.append(state)

        with (
            patch(
                "tgai_agent.agent_manager.agent.complete",
                new=AsyncMock(return_value="RESULT: Task done"),
            ),
            patch(
                "tgai_agent.agent_manager.agent.update_agent_memory",
                new=AsyncMock(),
            ),
            patch(
                "tgai_agent.agent_manager.agent.update_agent_state",
                new=mock_update_state,
            ),
            patch(
                "tgai_agent.agent_manager.agent.PluginRegistry.list_all",
                return_value=[],
            ),
        ):
            result = await agent.run_task("Do some research", context={})

        assert AgentState.RUNNING in states_recorded
        assert AgentState.IDLE in states_recorded
        assert agent.state == AgentState.IDLE

    async def test_run_task_returns_result(self):
        agent = _make_agent()
        mock_memory = MagicMock()
        mock_memory.add = AsyncMock()
        mock_memory.get_context = AsyncMock(return_value=[])
        agent._memory = mock_memory

        with (
            patch(
                "tgai_agent.agent_manager.agent.complete",
                new=AsyncMock(return_value="RESULT: Found 3 results"),
            ),
            patch(
                "tgai_agent.agent_manager.agent.update_agent_memory",
                new=AsyncMock(),
            ),
            patch(
                "tgai_agent.agent_manager.agent.update_agent_state",
                new=AsyncMock(),
            ),
            patch(
                "tgai_agent.agent_manager.agent.PluginRegistry.list_all",
                return_value=[],
            ),
        ):
            result = await agent.run_task("Research task", context={})

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_run_task_parses_tool_call(self):
        """When AI returns TOOL: call, the agent calls that plugin."""
        agent = _make_agent()
        mock_memory = MagicMock()
        mock_memory.add = AsyncMock()

        # First think() returns TOOL call, second returns RESULT
        call_count = 0

        async def mock_context_and_complete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [MagicMock()]
            return []

        mock_memory.get_context = AsyncMock(return_value=[])
        agent._memory = mock_memory

        responses = iter([
            'TOOL: web_search\nPARAMS: {"query": "Python tutorial"}\n',
            "RESULT: Python is great",
        ])

        async def mock_complete(user_id, provider, messages, **kwargs):
            return next(responses)

        mock_plugin_registry = MagicMock()
        mock_plugin_registry.run = AsyncMock(return_value="Search results: ...")
        mock_plugin_registry.list_all.return_value = []

        with (
            patch(
                "tgai_agent.agent_manager.agent.complete",
                new=mock_complete,
            ),
            patch(
                "tgai_agent.agent_manager.agent.update_agent_memory",
                new=AsyncMock(),
            ),
            patch(
                "tgai_agent.agent_manager.agent.update_agent_state",
                new=AsyncMock(),
            ),
            patch(
                "tgai_agent.agent_manager.agent.PluginRegistry",
                mock_plugin_registry,
            ),
        ):
            result = await agent.run_task("Search for Python", context={"user_id": 42})

        # The plugin should have been called
        mock_plugin_registry.run.assert_called_once()
        call_args = mock_plugin_registry.run.call_args
        assert call_args[0][0] == "web_search"

    async def test_run_task_already_running_returns_message(self):
        agent = _make_agent()
        agent.state = AgentState.RUNNING

        result = await agent.run_task("Another task", context={})
        assert "already running" in result.lower()

    async def test_run_task_state_restored_on_exception(self):
        """State should return to IDLE even if an error occurs."""
        agent = _make_agent()
        mock_memory = MagicMock()
        mock_memory.add = AsyncMock()
        mock_memory.get_context = AsyncMock(return_value=[])
        agent._memory = mock_memory

        with (
            patch(
                "tgai_agent.agent_manager.agent.complete",
                new=AsyncMock(side_effect=RuntimeError("crash")),
            ),
            patch(
                "tgai_agent.agent_manager.agent.update_agent_memory",
                new=AsyncMock(),
            ),
            patch(
                "tgai_agent.agent_manager.agent.update_agent_state",
                new=AsyncMock(),
            ),
            patch(
                "tgai_agent.agent_manager.agent.PluginRegistry.list_all",
                return_value=[],
            ),
        ):
            # run_task catches errors in think() — think() returns error string
            result = await agent.run_task("Crashing task", context={})

        # State should be IDLE after task completes (even on error)
        assert agent.state == AgentState.IDLE


class TestSubAgentStop:
    async def test_stop_sets_state_stopped(self):
        agent = _make_agent()

        with patch(
            "tgai_agent.agent_manager.agent.update_agent_state",
            new=AsyncMock(),
        ):
            await agent.stop()

        assert agent.state == AgentState.STOPPED

    async def test_stop_cancels_running_task(self):
        agent = _make_agent()
        mock_task = MagicMock()
        mock_task.done.return_value = False
        agent._task = mock_task

        with patch(
            "tgai_agent.agent_manager.agent.update_agent_state",
            new=AsyncMock(),
        ):
            await agent.stop()

        mock_task.cancel.assert_called_once()


class TestAgentState:
    def test_state_constants(self):
        assert AgentState.IDLE == "idle"
        assert AgentState.RUNNING == "running"
        assert AgentState.STOPPED == "stopped"

    def test_initial_state_is_idle(self):
        agent = _make_agent()
        assert agent.state == AgentState.IDLE

    def test_repr(self):
        agent = _make_agent()
        r = repr(agent)
        assert "TestAgent" in r
        assert "researcher" in r
