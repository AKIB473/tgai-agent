"""
ai_core/memory/long_term.py — Long-term memory via summarisation.

Periodically condenses old conversation history into a single "summary"
message that replaces the raw history, reducing token usage while
preserving meaningful context.
"""

from __future__ import annotations

from tgai_agent.ai_core.base_provider import AIMessage
from tgai_agent.ai_core.router import complete
from tgai_agent.storage.repositories.chat_repo import (
    append_message,
    clear_messages,
    get_messages,
)
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

SUMMARISE_THRESHOLD = 40  # Summarise when history exceeds this many messages
KEEP_RECENT = 10  # Keep these many recent messages after summarising


class LongTermMemory:
    """
    Optional long-term memory layer using summarisation.

    How it works:
        1. When message count exceeds SUMMARISE_THRESHOLD, ask the AI to
           summarise the oldest messages.
        2. Store the summary as a special 'system' message at the beginning
           of history, then delete the old messages.
        3. This keeps token counts manageable while preserving context.
    """

    def __init__(
        self,
        user_id: int,
        chat_id: int,
        provider: str = "openai",
        model: str | None = None,
    ) -> None:
        self.user_id = user_id
        self.chat_id = chat_id
        self.provider = provider
        self.model = model

    async def maybe_compress(self) -> bool:
        """
        Check if compression is needed; if so, summarise and replace old messages.
        Returns True if compression was performed.
        """
        history = await get_messages(self.user_id, self.chat_id, limit=200)
        if len(history) < SUMMARISE_THRESHOLD:
            return False

        # Split: older messages to summarise, recent to keep
        to_summarise = history[:-KEEP_RECENT]
        to_keep = history[-KEEP_RECENT:]

        conversation_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in to_summarise)

        summary_prompt = [
            AIMessage(
                "system",
                "You are a conversation summariser. Create a concise, factual summary "
                "of the following conversation, capturing key facts, decisions, and context "
                "that would be useful to remember in future turns.",
            ),
            AIMessage("user", conversation_text),
        ]

        try:
            summary = await complete(
                self.user_id,
                self.provider,
                summary_prompt,
                model=self.model,
                max_tokens=512,
            )
        except Exception as exc:
            log.warning("long_term_memory.summarise_failed", error=str(exc))
            return False

        # Replace history: delete all → insert summary → insert kept messages
        await clear_messages(self.user_id, self.chat_id)

        await append_message(
            self.user_id,
            self.chat_id,
            "system",
            f"[Memory Summary from earlier conversation]\n{summary}",
        )
        for msg in to_keep:
            await append_message(self.user_id, self.chat_id, msg["role"], msg["content"])

        log.info(
            "long_term_memory.compressed",
            user_id=self.user_id,
            chat_id=self.chat_id,
            summarised=len(to_summarise),
            kept=len(to_keep),
        )
        return True
