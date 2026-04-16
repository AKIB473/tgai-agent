"""
ai_core/memory/short_term.py — Sliding-window conversation memory.

Keeps the last N messages in memory (DB-backed) and formats them
for injection into AI provider calls.
"""

from __future__ import annotations

from typing import List

from tgai_agent.ai_core.base_provider import AIMessage
from tgai_agent.storage.repositories.chat_repo import (
    append_message,
    clear_messages,
    get_messages,
)
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

DEFAULT_WINDOW = 20   # messages to keep in context
MAX_WINDOW = 100


class ShortTermMemory:
    """
    Manages per-chat conversation history.
    Persists to DB so memory survives restarts.
    """

    def __init__(self, user_id: int, chat_id: int, window: int = DEFAULT_WINDOW) -> None:
        self.user_id = user_id
        self.chat_id = chat_id
        self.window = min(window, MAX_WINDOW)

    async def add(self, role: str, content: str) -> None:
        """Append a message to history."""
        await append_message(self.user_id, self.chat_id, role, content)

    async def get_context(
        self,
        system_prompt: str = "",
    ) -> List[AIMessage]:
        """
        Return a list of AIMessage objects ready for the provider.
        System prompt is always first; followed by the last `window` messages.
        """
        messages: List[AIMessage] = []

        if system_prompt:
            messages.append(AIMessage("system", system_prompt))

        history = await get_messages(self.user_id, self.chat_id, limit=self.window)
        for h in history:
            messages.append(AIMessage(h["role"], h["content"]))

        return messages

    async def clear(self) -> int:
        """Clear all messages for this chat. Returns rows deleted."""
        count = await clear_messages(self.user_id, self.chat_id)
        log.info("memory.cleared", user_id=self.user_id, chat_id=self.chat_id, rows=count)
        return count

    async def summary(self) -> str:
        """Return a brief string summary of current memory size."""
        history = await get_messages(self.user_id, self.chat_id, limit=MAX_WINDOW)
        return f"{len(history)} messages in memory (window={self.window})"
