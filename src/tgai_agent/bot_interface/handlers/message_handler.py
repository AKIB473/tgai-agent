"""
bot_interface/handlers/message_handler.py — Core incoming message handler.

Flow:
  1. Permission + rate-limit checks
  2. Resolve chat config (AI provider, model, system prompt, auto-reply)
  3. If auto_reply is off AND this is a new chat → ask user for permission
  4. Build context from short-term memory + optional long-term compression
  5. Call AI provider → stream response back
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from tgai_agent.ai_core.base_provider import AIMessage
from tgai_agent.ai_core.memory.long_term import LongTermMemory
from tgai_agent.ai_core.memory.short_term import ShortTermMemory
from tgai_agent.ai_core.router import complete
from tgai_agent.agent_manager.manager import talk_to_agent
from tgai_agent.bot_interface.menus.keyboards import auto_reply_prompt_menu
from tgai_agent.security.permissions import require_permission
from tgai_agent.security.rate_guard import is_rate_limited
from tgai_agent.storage.repositories.chat_repo import get_chat_config, upsert_chat_config
from tgai_agent.storage.repositories.user_repo import upsert_user
from tgai_agent.utils.helpers import truncate
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

# Maximum chars fed to the AI in a single user message
MAX_USER_MESSAGE_LEN = 4000


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main message handler — registered for all non-command text messages."""
    user = update.effective_user
    chat = update.effective_chat
    message = update.message

    if not user or not message or not message.text:
        return

    # ── 1. Permission check ─────────────────────────────────────────────
    if not await require_permission(user.id):
        return

    # ── 2. Rate limit ────────────────────────────────────────────────────
    if await is_rate_limited(user.id, chat.id):
        await message.reply_text(
            "⚠️ You're sending messages too fast. Please wait a moment."
        )
        return

    # ── Agent talk mode ──────────────────────────────────────────────────
    agent_id = context.user_data.get("talking_to_agent")
    if agent_id:
        if message.text.strip().lower() in ("/done", "/stop"):
            context.user_data.pop("talking_to_agent", None)
            await message.reply_text("👋 Stopped talking to agent. Back to normal mode.")
            return
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        response = await talk_to_agent(agent_id, user.id, message.text)
        await message.reply_text(truncate(response, 4096))
        return

    # ── 3. Register user ─────────────────────────────────────────────────
    await upsert_user(user.id, username=user.username, first_name=user.first_name)

    # ── 4. Load chat config ──────────────────────────────────────────────
    config = await get_chat_config(user.id, chat.id)

    # ── 5. Auto-reply gate ───────────────────────────────────────────────
    if not config.get("auto_reply"):
        # Check if we already asked for permission for this chat
        if not config.get("reply_confirmed"):
            await upsert_chat_config(
                user.id, chat.id,
                chat_title=chat.title or chat.first_name or str(chat.id),
                reply_confirmed=True,  # mark as asked so we don't spam
            )
            await message.reply_text(
                f"👋 Hi! I noticed a message in this chat.\n"
                f"Would you like me to auto-reply here?",
                reply_markup=auto_reply_prompt_menu(chat.id),
            )
        # Don't reply until user explicitly enables it
        return

    # ── 6. Typing indicator ──────────────────────────────────────────────
    await context.bot.send_chat_action(chat_id=chat.id, action="typing")

    # ── 7. Build memory context ──────────────────────────────────────────
    memory = ShortTermMemory(user.id, chat.id)
    user_text = truncate(message.text, MAX_USER_MESSAGE_LEN)
    await memory.add("user", user_text)

    # Optional: compress old history
    lt_memory = LongTermMemory(user.id, chat.id, config["ai_provider"], config["ai_model"])
    await lt_memory.maybe_compress()

    system_prompt = config.get("system_prompt", "You are a helpful AI assistant.")
    tone = config.get("tone", "neutral")
    full_system = f"{system_prompt}\n\nTone: {tone}"

    messages = await memory.get_context(system_prompt=full_system)

    # ── 8. Call AI ───────────────────────────────────────────────────────
    try:
        response = await complete(
            user_id=user.id,
            provider_name=config["ai_provider"],
            messages=messages,
            model=config["ai_model"],
        )
    except ValueError as exc:
        # Missing API key or unknown provider
        await message.reply_text(
            f"⚙️ Configuration needed: {exc}\n\nUse /config to set up your AI provider."
        )
        return
    except Exception as exc:
        log.error("message_handler.ai_error", user_id=user.id, error=str(exc))
        await message.reply_text("❌ AI error — please try again in a moment.")
        return

    # ── 9. Store response + reply ────────────────────────────────────────
    await memory.add("assistant", response)
    await message.reply_text(truncate(response, 4096))

    log.info(
        "message_handler.replied",
        user_id=user.id,
        chat_id=chat.id,
        provider=config["ai_provider"],
        chars=len(response),
    )
