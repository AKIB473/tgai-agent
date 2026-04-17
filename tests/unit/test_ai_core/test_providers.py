"""Tests for AI providers with mocked API clients."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tgai_agent.ai_core.base_provider import AIMessage
from tgai_agent.ai_core.providers.claude_provider import ClaudeProvider
from tgai_agent.ai_core.providers.openai_provider import OpenAIProvider


class TestOpenAIProvider:
    def test_init(self):
        p = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")
        assert p.api_key == "sk-test"
        assert p.model == "gpt-4o-mini"
        assert p.name == "openai"

    def test_default_model(self):
        p = OpenAIProvider(api_key="sk-test")
        assert p.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_complete_returns_string(self):
        provider = OpenAIProvider(api_key="sk-test")
        messages = [
            AIMessage("system", "You are helpful."),
            AIMessage("user", "Hello!"),
        ]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hi there!"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        with patch.object(provider, "_get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_fn.return_value = mock_client

            result = await provider.complete(messages)
            assert result == "Hi there!"
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_complete_passes_correct_model(self):
        provider = OpenAIProvider(api_key="sk-test", model="gpt-4o")
        messages = [AIMessage("user", "test")]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "ok"
        mock_response.usage = MagicMock(prompt_tokens=1, completion_tokens=1)

        with patch.object(provider, "_get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_fn.return_value = mock_client

            await provider.complete(messages)
            call_kwargs = mock_client.chat.completions.create.call_args
            assert call_kwargs.kwargs.get("model") == "gpt-4o"

    @pytest.mark.asyncio
    async def test_complete_empty_content_returns_empty_string(self):
        provider = OpenAIProvider(api_key="sk-test")
        messages = [AIMessage("user", "test")]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.usage = MagicMock(prompt_tokens=1, completion_tokens=0)

        with patch.object(provider, "_get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_fn.return_value = mock_client

            result = await provider.complete(messages)
            assert result == ""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        provider = OpenAIProvider(api_key="sk-test")
        messages = [AIMessage("user", "test")]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "recovered"
        mock_response.usage = MagicMock(prompt_tokens=1, completion_tokens=1)

        call_count = 0

        async def flaky(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary error")
            return mock_response

        with patch.object(provider, "_get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.chat.completions.create = flaky
            mock_client_fn.return_value = mock_client

            result = await provider.complete(messages)
            assert result == "recovered"
            assert call_count == 2


class TestGeminiProvider:
    def test_init(self):
        with patch("google.generativeai.configure"), patch("google.generativeai.GenerativeModel"):
            from tgai_agent.ai_core.providers.gemini_provider import GeminiProvider

            p = GeminiProvider(api_key="test-key")
            assert p.api_key == "test-key"
            assert p.name == "gemini"

    @pytest.mark.asyncio
    async def test_complete_returns_string(self):
        with (
            patch("google.generativeai.configure"),
            patch("google.generativeai.GenerativeModel") as mock_model_cls,
            patch("google.generativeai.GenerationConfig"),
        ):
            from tgai_agent.ai_core.providers.gemini_provider import GeminiProvider

            mock_model = MagicMock()
            mock_chat = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "Gemini response"
            mock_chat.send_message.return_value = mock_resp
            mock_model.start_chat.return_value = mock_chat
            mock_model_cls.return_value = mock_model

            provider = GeminiProvider(api_key="test-key")
            messages = [
                AIMessage("system", "Be helpful."),
                AIMessage("user", "Hello"),
            ]
            result = await provider.complete(messages)
            assert result == "Gemini response"

    @pytest.mark.asyncio
    async def test_system_message_becomes_leading_exchange(self):
        with (
            patch("google.generativeai.configure"),
            patch("google.generativeai.GenerativeModel") as mock_model_cls,
            patch("google.generativeai.GenerationConfig"),
        ):
            from tgai_agent.ai_core.providers.gemini_provider import GeminiProvider

            mock_model = MagicMock()
            mock_chat = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "ok"
            mock_chat.send_message.return_value = mock_resp
            mock_model.start_chat.return_value = mock_chat
            mock_model_cls.return_value = mock_model

            provider = GeminiProvider(api_key="test-key")
            messages = [
                AIMessage("system", "You are a pirate."),
                AIMessage("user", "Say hello"),
            ]
            await provider.complete(messages)
            call_kwargs = mock_model.start_chat.call_args
            history = call_kwargs.kwargs.get("history", [])
            assert len(history) >= 2
            assert history[0]["role"] == "user"
            assert "Instructions" in history[0]["parts"][0]
            assert history[1]["role"] == "model"


class TestClaudeProvider:
    def test_init(self):
        with patch("anthropic.AsyncAnthropic"):
            p = ClaudeProvider(api_key="sk-ant-test")
            assert p.api_key == "sk-ant-test"
            assert p.name == "claude"

    def test_default_model(self):
        with patch("anthropic.AsyncAnthropic"):
            p = ClaudeProvider(api_key="sk-ant-test")
            assert "claude" in p.model

    @pytest.mark.asyncio
    async def test_complete_returns_string(self):
        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Claude response")]
            mock_response.usage.input_tokens = 10
            mock_response.usage.output_tokens = 5
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            provider = ClaudeProvider(api_key="sk-ant-test")
            messages = [
                AIMessage("system", "You are helpful."),
                AIMessage("user", "Hello"),
            ]
            result = await provider.complete(messages)
            assert result == "Claude response"

    @pytest.mark.asyncio
    async def test_system_messages_separated(self):
        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="ok")]
            mock_response.usage = MagicMock(input_tokens=1, output_tokens=1)
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            provider = ClaudeProvider(api_key="sk-ant-test")
            messages = [
                AIMessage("system", "System instructions here."),
                AIMessage("user", "Hello"),
            ]
            await provider.complete(messages)
            call_kwargs = mock_client.messages.create.call_args
            assert "system" in call_kwargs.kwargs
            chat_messages = call_kwargs.kwargs.get("messages", [])
            assert all(m["role"] != "system" for m in chat_messages)

    @pytest.mark.asyncio
    async def test_empty_content_returns_empty_string(self):
        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = []
            mock_response.usage = MagicMock(input_tokens=1, output_tokens=0)
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            provider = ClaudeProvider(api_key="sk-ant-test")
            messages = [AIMessage("user", "Hello")]
            result = await provider.complete(messages)
            assert result == ""
