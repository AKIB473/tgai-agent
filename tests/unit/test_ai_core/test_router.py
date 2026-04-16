"""Tests for the AI provider router."""

import pytest
from unittest.mock import AsyncMock, patch

from tgai_agent.ai_core.router import get_provider, list_providers
from tgai_agent.ai_core.base_provider import AIMessage


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
    with patch(
        "tgai_agent.ai_core.router.get_api_key",
        new=AsyncMock(return_value=""),
    ):
        with pytest.raises(ValueError, match="No API key"):
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
