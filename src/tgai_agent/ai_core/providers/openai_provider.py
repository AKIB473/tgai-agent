"""
ai_core/providers/openai_provider.py — OpenAI ChatCompletion provider.
"""

from __future__ import annotations

from openai import AsyncOpenAI

from tgai_agent.ai_core.base_provider import AIMessage, BaseAIProvider
from tgai_agent.utils.logger import get_logger
from tgai_agent.utils.retry import async_retry

log = get_logger(__name__)


class OpenAIProvider(BaseAIProvider):
    name = "openai"
    default_model = "gpt-4o-mini"
    supports_streaming = True

    def __init__(self, api_key: str, model: str | None = None) -> None:
        super().__init__(api_key, model)
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    @async_retry(max_attempts=3, wait_seconds=2, exceptions=(Exception,))
    async def complete(
        self,
        messages: list[AIMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        log.debug(
            "openai.complete",
            model=self.model,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
        )
        return content
