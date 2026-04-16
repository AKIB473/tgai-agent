"""Tests for AIMessage and BaseAIProvider contract."""

import pytest
from tgai_agent.ai_core.base_provider import AIMessage, BaseAIProvider


def test_aimessage_to_dict():
    msg = AIMessage("user", "Hello!")
    assert msg.to_dict() == {"role": "user", "content": "Hello!"}


def test_aimessage_from_dict():
    msg = AIMessage.from_dict({"role": "assistant", "content": "Hi there"})
    assert msg.role == "assistant"
    assert msg.content == "Hi there"


def test_aimessage_repr():
    msg = AIMessage("user", "A" * 100)
    assert "AIMessage" in repr(msg)
    assert len(repr(msg)) < 80  # truncated


class _ConcreteProvider(BaseAIProvider):
    name = "test"
    default_model = "test-model"

    async def complete(self, messages, **kwargs) -> str:
        return "test response"


def test_provider_init():
    p = _ConcreteProvider(api_key="test-key")
    assert p.model == "test-model"
    assert p.api_key == "test-key"


def test_provider_custom_model():
    p = _ConcreteProvider(api_key="key", model="custom-model")
    assert p.model == "custom-model"


@pytest.mark.asyncio
async def test_provider_complete():
    p = _ConcreteProvider(api_key="key")
    result = await p.complete([AIMessage("user", "hi")])
    assert result == "test response"
