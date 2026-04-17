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
        import asyncio

        system_parts = [m.content for m in messages if m.role == "system"]
        user_msgs = [m for m in messages if m.role != "system"]

        history = []
        if system_parts:
            system_text = "\n\n".join(system_parts)
            history.append({"role": "user", "parts": [f"[Instructions]\n{system_text}"]})
            history.append({"role": "model", "parts": ["Understood. I will follow these instructions."]})

        for msg in user_msgs[:-1]:
            role = "model" if msg.role == "assistant" else "user"
            history.append({"role": role, "parts": [msg.content]})

        prompt = user_msgs[-1].content if user_msgs else ""

        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        def _sync_call() -> str:
            chat = self._model_instance.start_chat(history=history)
            response = chat.send_message(prompt, generation_config=generation_config)
            return response.text or ""

        text = await asyncio.to_thread(_sync_call)
        log.debug("gemini.complete", model=self.model, chars=len(text))
        return text
