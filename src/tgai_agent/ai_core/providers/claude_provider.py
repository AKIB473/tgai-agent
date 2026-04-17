"""
ai_core/providers/claude_provider.py — Anthropic Claude provider.
"""

from __future__ import annotations

from typing import List

import anthropic

from tgai_agent.ai_core.base_provider import AIMessage, BaseAIProvider
from tgai_agent.utils.logger import get_logger
from tgai_agent.utils.retry import async_retry

log = get_logger(__name__)


class ClaudeProvider(BaseAIProvider):
    name = "claude"
    default_model = "claude-3-5-haiku-20241022"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        super().__init__(api_key, model)
        self._client = anthropic.AsyncAnthropic(api_key=self.api_key)

    @async_retry(max_attempts=3, wait_seconds=2, exceptions=(Exception,))
    async def complete(
        self,
        messages: list[AIMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        # Separate system messages (Claude API handles them differently)
        system_parts = [m.content for m in messages if m.role == "system"]
        chat_messages = [
            {"role": m.role, "content": m.content} for m in messages if m.role != "system"
        ]
        system_prompt = "\n\n".join(system_parts) if system_parts else anthropic.NOT_GIVEN

        response = await self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=chat_messages,
            temperature=temperature,
        )
        text = response.content[0].text if response.content else ""
        log.debug(
            "claude.complete",
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return text
