"""
Tests for the message_handler (bot_interface/handlers/message_handler.py).

Tests:
- Banned user gets no response
- Rate-limited user gets warning message
- Agent talk mode routes to agent, not main AI
- /done exits agent talk mode
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_update(user_id: int, chat_id: int, text: str = "Hello"):
    """Build a minimal fake Telegram Update object."""
    user = MagicMock()
    user.id = user_id
    user.username = "testuser"
    user.first_name = "Test"

    chat = MagicMock()
    chat.id = chat_id
    chat.title = "Test Chat"
    chat.first_name = "Test"

    message = MagicMock()
    message.text = text
    message.reply_text = AsyncMock()

    update = MagicMock()
    update.effective_user = user
    update.effective_chat = chat
    update.message = message
    return update


def _make_context(user_data: dict | None = None):
    """Build a minimal fake telegram Context."""
    context = MagicMock()
    context.user_data = user_data or {}
    context.args = []
    context.bot = MagicMock()
    context.bot.send_chat_action = AsyncMock()
    return context


class TestMessageHandlerBannedUser:
    async def test_banned_user_gets_no_response(self):
        """Banned user: require_permission returns False → handler returns early."""
        from tgai_agent.bot_interface.handlers.message_handler import handle_message

        update = _make_update(user_id=666, chat_id=100, text="Hello")
        context = _make_context()

        with patch(
            "tgai_agent.bot_interface.handlers.message_handler.require_permission",
            new=AsyncMock(return_value=False),
        ):
            await handle_message(update, context)

        # No reply should be sent
        update.message.reply_text.assert_not_called()

    async def test_permitted_user_proceeds(self):
        """A permitted, non-rate-limited user with auto_reply enabled gets a response."""
        from tgai_agent.bot_interface.handlers.message_handler import handle_message

        update = _make_update(user_id=42, chat_id=100, text="Tell me something")
        context = _make_context()

        mock_config = {
            "ai_provider": "openai",
            "ai_model": "gpt-4o-mini",
            "system_prompt": "Be helpful",
            "auto_reply": True,
            "reply_confirmed": True,
            "tone": "neutral",
        }

        with (
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.require_permission",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.is_rate_limited",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.upsert_user",
                new=AsyncMock(),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.get_chat_config",
                new=AsyncMock(return_value=mock_config),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.ShortTermMemory"
            ) as mock_stm_cls,
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.LongTermMemory"
            ) as mock_ltm_cls,
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.complete",
                new=AsyncMock(return_value="AI response here"),
            ),
        ):
            mock_stm = MagicMock()
            mock_stm.add = AsyncMock()
            mock_stm.get_context = AsyncMock(return_value=[])
            mock_stm_cls.return_value = mock_stm

            mock_ltm = MagicMock()
            mock_ltm.maybe_compress = AsyncMock(return_value=False)
            mock_ltm_cls.return_value = mock_ltm

            await handle_message(update, context)

        update.message.reply_text.assert_called_once()
        args = update.message.reply_text.call_args[0]
        assert "AI response here" in args[0]


class TestMessageHandlerRateLimit:
    async def test_rate_limited_user_gets_warning(self):
        """Rate-limited user should receive warning message."""
        from tgai_agent.bot_interface.handlers.message_handler import handle_message

        update = _make_update(user_id=99, chat_id=200, text="spam")
        context = _make_context()

        with (
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.require_permission",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.is_rate_limited",
                new=AsyncMock(return_value=True),
            ),
        ):
            await handle_message(update, context)

        # Should reply with a warning
        update.message.reply_text.assert_called_once()
        warning_text = update.message.reply_text.call_args[0][0]
        assert "wait" in warning_text.lower() or "fast" in warning_text.lower()

    async def test_rate_limited_no_ai_call(self):
        """Rate-limited user must NOT trigger AI call."""
        from tgai_agent.bot_interface.handlers.message_handler import handle_message

        update = _make_update(user_id=99, chat_id=200, text="spam")
        context = _make_context()

        with (
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.require_permission",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.is_rate_limited",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.complete",
            ) as mock_complete,
        ):
            await handle_message(update, context)

        mock_complete.assert_not_called()


class TestAgentTalkMode:
    async def test_agent_talk_mode_routes_to_agent(self):
        """When talking_to_agent is set, route to talk_to_agent(), not main AI."""
        from tgai_agent.bot_interface.handlers.message_handler import handle_message

        update = _make_update(user_id=42, chat_id=100, text="Do a task")
        context = _make_context(user_data={"talking_to_agent": "agent-uuid-123"})

        with (
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.require_permission",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.is_rate_limited",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.talk_to_agent",
                new=AsyncMock(return_value="Agent response"),
            ) as mock_talk,
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.complete",
            ) as mock_complete,
        ):
            await handle_message(update, context)

        # Should call talk_to_agent, not the main AI complete
        mock_talk.assert_called_once_with("agent-uuid-123", 42, "Do a task")
        mock_complete.assert_not_called()
        update.message.reply_text.assert_called_once()

    async def test_done_command_exits_agent_talk_mode(self):
        """Sending /done should exit agent talk mode."""
        from tgai_agent.bot_interface.handlers.message_handler import handle_message

        update = _make_update(user_id=42, chat_id=100, text="/done")
        context = _make_context(user_data={"talking_to_agent": "agent-uuid-123"})

        with (
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.require_permission",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.is_rate_limited",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.talk_to_agent",
                new=AsyncMock(),
            ) as mock_talk,
        ):
            await handle_message(update, context)

        # Agent talk mode should be cleared
        assert "talking_to_agent" not in context.user_data
        # Should send a goodbye message
        update.message.reply_text.assert_called_once()
        reply_text = update.message.reply_text.call_args[0][0]
        assert (
            "stop" in reply_text.lower()
            or "normal" in reply_text.lower()
            or "agent" in reply_text.lower()
        )
        # Should NOT have called talk_to_agent for the /done message
        mock_talk.assert_not_called()

    async def test_stop_command_also_exits_agent_talk_mode(self):
        """Sending /stop should also exit agent talk mode."""
        from tgai_agent.bot_interface.handlers.message_handler import handle_message

        update = _make_update(user_id=42, chat_id=100, text="/stop")
        context = _make_context(user_data={"talking_to_agent": "agent-uuid-456"})

        with (
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.require_permission",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.is_rate_limited",
                new=AsyncMock(return_value=False),
            ),
        ):
            await handle_message(update, context)

        assert "talking_to_agent" not in context.user_data

    async def test_auto_reply_off_sends_prompt(self):
        """When auto_reply=False and reply_confirmed=False, send permission prompt."""
        from tgai_agent.bot_interface.handlers.message_handler import handle_message

        update = _make_update(user_id=42, chat_id=100, text="Hello")
        context = _make_context()

        mock_config = {
            "ai_provider": "openai",
            "ai_model": "gpt-4o-mini",
            "system_prompt": "",
            "auto_reply": False,
            "reply_confirmed": False,
            "tone": "neutral",
        }

        with (
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.require_permission",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.is_rate_limited",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.upsert_user",
                new=AsyncMock(),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.get_chat_config",
                new=AsyncMock(return_value=mock_config),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.upsert_chat_config",
                new=AsyncMock(),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.auto_reply_prompt_menu",
                return_value=MagicMock(),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.complete",
            ) as mock_complete,
        ):
            await handle_message(update, context)

        # Should prompt for permission, not call AI
        mock_complete.assert_not_called()
        update.message.reply_text.assert_called_once()

    async def test_missing_api_key_sends_config_message(self):
        """ValueError (missing API key) should send a config prompt."""
        from tgai_agent.bot_interface.handlers.message_handler import handle_message

        update = _make_update(user_id=42, chat_id=100, text="Hello AI")
        context = _make_context()

        mock_config = {
            "ai_provider": "openai",
            "ai_model": "gpt-4o-mini",
            "system_prompt": "Be helpful",
            "auto_reply": True,
            "reply_confirmed": True,
            "tone": "neutral",
        }

        with (
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.require_permission",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.is_rate_limited",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.upsert_user",
                new=AsyncMock(),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.get_chat_config",
                new=AsyncMock(return_value=mock_config),
            ),
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.ShortTermMemory"
            ) as mock_stm_cls,
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.LongTermMemory"
            ) as mock_ltm_cls,
            patch(
                "tgai_agent.bot_interface.handlers.message_handler.complete",
                new=AsyncMock(side_effect=ValueError("No API key available")),
            ),
        ):
            mock_stm = MagicMock()
            mock_stm.add = AsyncMock()
            mock_stm.get_context = AsyncMock(return_value=[])
            mock_stm_cls.return_value = mock_stm

            mock_ltm = MagicMock()
            mock_ltm.maybe_compress = AsyncMock(return_value=False)
            mock_ltm_cls.return_value = mock_ltm

            await handle_message(update, context)

        # Should reply with config prompt
        update.message.reply_text.assert_called_once()
        reply = update.message.reply_text.call_args[0][0]
        assert "/config" in reply or "configuration" in reply.lower()
