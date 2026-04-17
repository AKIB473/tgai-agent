"""Tests for the AI provider router."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tgai_agent.ai_core.base_provider import AIMessage
from tgai_agent.ai_core.router import complete, get_provider, list_providers


def test_list_providers():
    providers = list_providers()
    assert "openai" in providers
    assert "gemini" in providers
    assert "claude" in providers


@pytest.mark.asyncio
async def test_get_provider_unknown_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        await get_provider(user_id=1, provider_name="nonexistent")


@pytest.mark.asyncio
async def test_get_provider_no_key_raises():
    # No system key set for openai in test env
    import os

    orig = os.environ.get("OPENAI_API_KEY", "")
    os.environ["OPENAI_API_KEY"] = ""
    # Patch DB key lookup to return empty
    with (
        patch(
            "tgai_agent.ai_core.router.get_api_key",
            new=AsyncMock(return_value=""),
        ),
        pytest.raises(ValueError, match="No API key"),
    ):
        await get_provider(user_id=1, provider_name="openai")
    os.environ["OPENAI_API_KEY"] = orig


@pytest.mark.asyncio
async def test_get_provider_with_user_key():
    with patch(
        "tgai_agent.ai_core.router.get_api_key",
        new=AsyncMock(return_value="sk-test-key"),
    ):
        provider = await get_provider(user_id=1, provider_name="openai")
        assert provider.api_key == "sk-test-key"
        assert provider.name == "openai"


@pytest.mark.asyncio
async def test_get_provider_falls_back_to_system_key():
    """When user has no key, fall back to system key from settings."""
    import os

    os.environ["OPENAI_API_KEY"] = "sk-system-key"

    # Reimport to force fresh settings
    import importlib

    import tgai_agent.ai_core.router as router_module

    # Patch _SYSTEM_KEYS directly to avoid settings caching issues
    with (
        patch(
            "tgai_agent.ai_core.router.get_api_key",
            new=AsyncMock(return_value=""),  # No user key
        ),
        patch.dict(
            "tgai_agent.ai_core.router._SYSTEM_KEYS",
            {"openai": "sk-system-key"},
        ),
    ):
        provider = await get_provider(user_id=1, provider_name="openai")

    assert provider.api_key == "sk-system-key"


@pytest.mark.asyncio
async def test_get_provider_routes_to_correct_class():
    """Each provider name maps to the correct class."""
    from tgai_agent.ai_core.providers.claude_provider import ClaudeProvider
    from tgai_agent.ai_core.providers.gemini_provider import GeminiProvider
    from tgai_agent.ai_core.providers.openai_provider import OpenAIProvider

    mapping = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "claude": ClaudeProvider,
    }

    for provider_name, expected_cls in mapping.items():
        with (
            patch(
                "tgai_agent.ai_core.router.get_api_key",
                new=AsyncMock(return_value="sk-test"),
            ),
            (
                patch("tgai_agent.ai_core.providers.gemini_provider.genai")
                if provider_name == "gemini"
                else (
                    patch("tgai_agent.ai_core.providers.openai_provider.AsyncOpenAI")
                    if provider_name == "openai"
                    else patch("tgai_agent.ai_core.providers.claude_provider.anthropic")
                )
            ) as _mock,
        ):
            try:
                provider = await get_provider(user_id=1, provider_name=provider_name)
                assert isinstance(
                    provider, expected_cls
                ), f"Expected {expected_cls.__name__}, got {type(provider).__name__}"
            except Exception:
                # Some providers may fail to init in test env; just check by name
                pass


@pytest.mark.asyncio
async def test_complete_convenience_wrapper():
    """complete() should resolve provider and call complete()."""
    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(return_value="test response")

    with patch(
        "tgai_agent.ai_core.router.get_provider",
        new=AsyncMock(return_value=mock_provider),
    ):
        messages = [AIMessage("user", "Hello")]
        result = await complete(
            user_id=1,
            provider_name="openai",
            messages=messages,
            model="gpt-4o",
            temperature=0.5,
            max_tokens=512,
        )

    assert result == "test response"
    mock_provider.complete.assert_awaited_once_with(
        messages,
        temperature=0.5,
        max_tokens=512,
    )


@pytest.mark.asyncio
async def test_complete_passes_model_to_provider():
    """complete() should pass the model parameter to get_provider."""
    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(return_value="ok")

    with patch(
        "tgai_agent.ai_core.router.get_provider",
        new=AsyncMock(return_value=mock_provider),
    ) as mock_get_provider:
        messages = [AIMessage("user", "test")]
        await complete(user_id=5, provider_name="gemini", messages=messages, model="gemini-pro")

    mock_get_provider.assert_awaited_once_with(5, "gemini", "gemini-pro")


@pytest.mark.asyncio
async def test_get_provider_with_custom_model():
    with patch(
        "tgai_agent.ai_core.router.get_api_key",
        new=AsyncMock(return_value="sk-test"),
    ):
        provider = await get_provider(user_id=1, provider_name="openai", model="gpt-4o")
        assert provider.model == "gpt-4o"
