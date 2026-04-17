"""
ai_core/base_provider.py — Abstract base class all AI providers must implement.

Every provider takes a list of messages (OpenAI-style dicts) and returns
a string response. This keeps the rest of the system provider-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AIMessage:
    """Lightweight message model shared across providers."""

    __slots__ = ("role", "content")

    def __init__(self, role: str, content: str) -> None:
        self.role = role  # 'system' | 'user' | 'assistant'
        self.content = content

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}

    @classmethod
    def from_dict(cls, d: dict) -> AIMessage:
        return cls(role=d["role"], content=d["content"])

    def __repr__(self) -> str:
        return f"AIMessage(role={self.role!r}, content={self.content[:40]!r})"


class BaseAIProvider(ABC):
    """
    All AI providers inherit from this class.

    Subclasses must implement:
        - `complete(messages, **kwargs) -> str`
        - `name` class attribute (e.g. "openai")
        - `default_model` class attribute (e.g. "gpt-4o-mini")
    """

    name: str = ""
    default_model: str = ""
    supports_streaming: bool = False

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self.api_key = api_key
        self.model = model or self.default_model

    @abstractmethod
    async def complete(
        self,
        messages: list[AIMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """
        Send messages to the AI and return the response text.
        Raises RuntimeError on API failure after retries.
        """

    async def health_check(self) -> bool:
        """
        Validate the API key works. Returns True if healthy.
        Default implementation: attempt a minimal completion.
        """
        try:
            probe = [
                AIMessage("system", "You are a test assistant."),
                AIMessage("user", "Reply with exactly: OK"),
            ]
            result = await self.complete(probe, max_tokens=5)
            return bool(result)
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"
