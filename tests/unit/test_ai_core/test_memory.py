"""Tests for short-term conversation memory."""

import pytest
from unittest.mock import AsyncMock, patch

from tgai_agent.ai_core.memory.short_term import ShortTermMemory
from tgai_agent.ai_core.base_provider import AIMessage


@pytest.mark.asyncio
async def test_get_context_with_system_prompt():
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
    ]
    with patch("tgai_agent.ai_core.memory.short_term.get_messages", new=AsyncMock(return_value=history)), \
         patch("tgai_agent.ai_core.memory.short_term.append_message", new=AsyncMock()):
        mem = ShortTermMemory(user_id=1, chat_id=1)
        messages = await mem.get_context(system_prompt="You are helpful.")

    assert messages[0].role == "system"
    assert messages[0].content == "You are helpful."
    assert messages[1].role == "user"
    assert messages[2].role == "assistant"


@pytest.mark.asyncio
async def test_get_context_empty_history():
    with patch("tgai_agent.ai_core.memory.short_term.get_messages", new=AsyncMock(return_value=[])), \
         patch("tgai_agent.ai_core.memory.short_term.append_message", new=AsyncMock()):
        mem = ShortTermMemory(user_id=1, chat_id=1)
        messages = await mem.get_context()
    assert messages == []


@pytest.mark.asyncio
async def test_add_message():
    with patch("tgai_agent.ai_core.memory.short_term.append_message", new=AsyncMock()) as mock_append:
        mem = ShortTermMemory(user_id=42, chat_id=99)
        await mem.add("user", "test message")
        mock_append.assert_awaited_once_with(42, 99, "user", "test message")


@pytest.mark.asyncio
async def test_clear():
    with patch("tgai_agent.ai_core.memory.short_term.clear_messages", new=AsyncMock(return_value=5)) as mock_clear:
        mem = ShortTermMemory(user_id=1, chat_id=1)
        count = await mem.clear()
        assert count == 5
        mock_clear.assert_awaited_once()
