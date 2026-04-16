"""
ai_core/providers/gemini_provider.py — Google Gemini provider.
"""

from __future__ import annotations

from typing import List

import google.generativeai as genai

from tgai_agent.ai_core.base_provider import AIMessage, BaseAIProvider
from tgai_agent.utils.logger import get_logger
from tgai_agent.utils.retry import async_retry

log = get_logger(__name__)

# Gemini uses a slightly different role naming
_ROLE_MAP = {"user": "user", "assistant": "model", "system": "user"}


class GeminiProvider(BaseAIProvider):
    name = "gemini"
    default_model = "gemini-1.5-flash"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        super().__init__(api_key, model)
        genai.configure(api_key=self.api_key)
        self._model_instance = genai.GenerativeModel(self.model)

    @async_retry(max_attempts=3, wait_seconds=2, exceptions=(Exception,))
    async def complete(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        # Gemini doesn't have a native system role in the history API;
        # prepend system messages as user turns.
        history = []
        prompt = ""

        for msg in messages:
            if msg.role == "system":
                # Inject system instructions as a leading user message
                history.append({"role": "user", "parts": [f"[System Instructions]\n{msg.content}"]})
                history.append({"role": "model", "parts": ["Understood. I'll follow these instructions."]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [msg.content]})
            else:
                prompt = msg.content  # last user message is the actual prompt

        # Use chat session for multi-turn history
        chat = self._model_instance.start_chat(history=history[:-1] if history else [])
        response = await chat.send_message_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        text = response.text or ""
        log.debug("gemini.complete", model=self.model, chars=len(text))
        return text
