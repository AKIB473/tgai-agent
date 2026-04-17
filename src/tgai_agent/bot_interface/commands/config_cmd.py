"""
bot_interface/commands/config_cmd.py — /config command and config conversation.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tgai_agent.bot_interface.menus.keyboards import config_menu
from tgai_agent.security.permissions import require_permission
from tgai_agent.storage.repositories.chat_repo import (
    get_chat_config,
    save_api_key,
    upsert_chat_config,
)
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

# Conversation states
AWAIT_API_KEY = 1
AWAIT_PROMPT = 2


async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not await require_permission(user.id):
        return

    chat_id = update.effective_chat.id
    config = await get_chat_config(user.id, chat_id)

    text = (
        f"⚙️ *Chat Configuration*\n\n"
        f"Provider: `{config.get('ai_provider', 'openai')}`\n"
        f"Model: `{config.get('ai_model', 'gpt-4o-mini')}`\n"
        f"Tone: `{config.get('tone', 'neutral')}`\n"
        f"Auto-reply: `{'✅ On' if config.get('auto_reply') else '❌ Off'}`\n"
        f"Language: `{config.get('language', 'en')}`\n\n"
        "Use the buttons below to change settings:"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=config_menu())


async def handle_set_api_key_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Called when user taps 'Set API Key' — start conversation."""
    query = update.callback_query
    await query.answer()
    context.user_data["config_action"] = "set_key"
    await query.edit_message_text(
        "🔑 Please send your API key.\n\n"
        "Format: `PROVIDER:your_api_key_here`\n"
        "Example: `openai:sk-abc123...`\n\n"
        "⚠️ Your key will be encrypted and stored securely.",
        parse_mode="Markdown",
    )
    return AWAIT_API_KEY


async def receive_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    text = update.message.text.strip()

    # Delete the message immediately to avoid key exposure in chat
    try:
        await update.message.delete()
    except Exception:
        pass

    if ":" not in text:
        await update.message.reply_text(
            "❌ Invalid format. Use `PROVIDER:api_key` (e.g. `openai:sk-...`)",
            parse_mode="Markdown",
        )
        return AWAIT_API_KEY

    provider, api_key = text.split(":", 1)
    provider = provider.strip().lower()
    api_key = api_key.strip()

    valid_providers = {"openai", "gemini", "claude"}
    if provider not in valid_providers:
        await context.bot.send_message(
            user.id,
            f"❌ Unknown provider '{provider}'. Choose from: {', '.join(valid_providers)}",
        )
        return AWAIT_API_KEY

    await save_api_key(user.id, provider, api_key)
    await context.bot.send_message(
        user.id,
        f"✅ API key for *{provider}* saved securely!",
        parse_mode="Markdown",
    )
    log.info("config.api_key_saved", user_id=user.id, provider=provider)
    return ConversationHandler.END


async def handle_set_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✏️ Send your custom system prompt.\n\n"
        "This defines how the AI behaves in this chat.\n"
        "Example: *You are a helpful assistant who speaks like a pirate.*",
        parse_mode="Markdown",
    )
    return AWAIT_PROMPT


async def receive_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    chat_id = update.effective_chat.id
    prompt = update.message.text.strip()

    await upsert_chat_config(user.id, chat_id, system_prompt=prompt)
    await update.message.reply_text(
        "✅ System prompt updated!",
        reply_markup=config_menu(),
    )
    return ConversationHandler.END


async def cancel_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Configuration cancelled.")
    return ConversationHandler.END


def build_config_conversation() -> ConversationHandler:
    """Build the config ConversationHandler (register in bot.py)."""
    return ConversationHandler(
        entry_points=[CommandHandler("config", config_command)],
        states={
            AWAIT_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_key)],
            AWAIT_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prompt)],
        },
        fallbacks=[CommandHandler("cancel", cancel_config)],
        allow_reentry=True,
    )
