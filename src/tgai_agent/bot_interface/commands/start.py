"""
bot_interface/commands/start.py — /start command handler.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from tgai_agent.bot_interface.menus.keyboards import main_menu
from tgai_agent.config import settings
from tgai_agent.security.permissions import require_permission
from tgai_agent.storage.repositories.user_repo import upsert_user
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

WELCOME_TEXT = """
👋 *Welcome to the AI Agent Platform!*

I'm your intelligent Telegram assistant powered by state-of-the-art AI.

Here's what I can do:
• 🤖 Run autonomous AI sub-agents for any task
• 💬 Have context-aware conversations in any chat
• 📋 Schedule tasks (one-time or recurring)
• 🔌 Use plugins (web search, code runner, summariser)
• 🔑 Connect your own AI provider (OpenAI, Gemini, Claude)
• 🧠 Remember your conversations over time

*Get started:*
1. Use /config to set up your AI provider
2. Use /agents to create your first agent
3. Just chat with me — I'll handle the rest!

Need help? Use /help at any time.
""".strip()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    # Register / upsert user in DB
    is_admin = user.id in settings.admin_ids
    await upsert_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        is_admin=is_admin,
    )

    # Check ban
    if not await require_permission(user.id):
        await update.message.reply_text("❌ You have been banned from using this bot.")
        return

    log.info("bot.start", user_id=user.id, username=user.username)

    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )
