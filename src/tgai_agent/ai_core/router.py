"""
ai_core/router.py — Dynamic provider routing.

Resolves the correct AI provider for a given user and chat,
injecting their API key. Falls back to system-level keys if no
user key is configured.
"""

from __future__ import annotations


from tgai_agent.ai_core.base_provider import AIMessage, BaseAIProvider
from tgai_agent.ai_core.providers.claude_provider import ClaudeProvider
from tgai_agent.ai_core.providers.gemini_provider import GeminiProvider
from tgai_agent.ai_core.providers.openai_provider import OpenAIProvider
from tgai_agent.config import settings
from tgai_agent.storage.repositories.chat_repo import get_api_key
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

# Registry: provider name → class
_PROVIDER_REGISTRY: dict[str, type[BaseAIProvider]] = {
    OpenAIProvider.name: OpenAIProvider,
    GeminiProvider.name: GeminiProvider,
    ClaudeProvider.name: ClaudeProvider,
}

# System-level fallback keys from .env
_SYSTEM_KEYS: dict[str, str] = {
    "openai": settings.openai_api_key,
    "gemini": settings.gemini_api_key,
    "claude": settings.claude_api_key,
}


def list_providers() -> list[str]:
    return list(_PROVIDER_REGISTRY.keys())


async def get_provider(
    user_id: int,
    provider_name: str,
    model: str | None = None,
) -> BaseAIProvider:
    """
    Return an initialised provider for the given user.

    Key resolution order:
      1. User's own key stored in DB
      2. System-level key from .env
      3. Raise ValueError if neither available
    """
    cls = _PROVIDER_REGISTRY.get(provider_name)
    if cls is None:
        raise ValueError(
            f"Unknown provider '{provider_name}'. " f"Available: {list(_PROVIDER_REGISTRY.keys())}"
        )

    api_key = await get_api_key(user_id, provider_name)
    if not api_key:
        api_key = _SYSTEM_KEYS.get(provider_name, "")
    if not api_key:
        raise ValueError(
            f"No API key available for provider '{provider_name}'. " f"Use /config to add your key."
        )

    log.debug("ai_router.resolved", provider=provider_name, model=model)
    return cls(api_key=api_key, model=model)


async def complete(
    user_id: int,
    provider_name: str,
    messages: list[AIMessage],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Convenience wrapper: resolve provider and call complete()."""
    provider = await get_provider(user_id, provider_name, model)
    return await provider.complete(messages, temperature=temperature, max_tokens=max_tokens)
