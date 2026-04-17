"""
bot_interface/bot.py — Bot initialisation and handler registration.

Builds the python-telegram-bot Application and wires all handlers.
"""

from __future__ import annotations

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from tgai_agent.bot_interface.commands.agents_cmd import agents_command
from tgai_agent.bot_interface.commands.config_cmd import build_config_conversation, config_command
from tgai_agent.bot_interface.commands.start import start_command
from tgai_agent.bot_interface.commands.tasks_cmd import tasks_command
from tgai_agent.bot_interface.handlers.callback_handler import handle_callback
from tgai_agent.bot_interface.handlers.message_handler import handle_message
from tgai_agent.config import settings
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


def build_application() -> Application:
    """
    Construct and return a fully-configured Application instance.
    Does NOT call .run_polling() — that happens in main.py.
    """
    app = Application.builder().token(settings.bot_token).build()

    # ── Commands ─────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("agents", agents_command))
    app.add_handler(CommandHandler("tasks", tasks_command))

    # Config uses a ConversationHandler for multi-step input
    app.add_handler(build_config_conversation())

    # Memory command
    app.add_handler(CommandHandler("memory", _memory_command))

    # Plugins command
    app.add_handler(CommandHandler("plugins", _plugins_command))

    # Status command
    app.add_handler(CommandHandler("status", _status_command))

    # Help command
    app.add_handler(CommandHandler("help", _help_command))

    # ── Callbacks ─────────────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(handle_callback))

    # ── Messages ─────────────────────────────────────────────────────────
    # Non-command text messages — handled last
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("bot.handlers_registered")
    return app


# ── Standalone command handlers defined here for brevity ─────────────────────


async def _memory_command(update, context) -> None:
    from tgai_agent.ai_core.memory.short_term import ShortTermMemory
    from tgai_agent.security.permissions import require_permission

    user = update.effective_user
    if not await require_permission(user.id):
        return

    chat_id = update.effective_chat.id
    memory = ShortTermMemory(user.id, chat_id)
    summary = await memory.summary()

    args = context.args
    if args and args[0].lower() == "clear":
        count = await memory.clear()
        await update.message.reply_text(f"🧹 Cleared {count} messages from memory.")
        return

    await update.message.reply_text(
        f"🧠 *Memory Status*\n\n{summary}\n\nUse `/memory clear` to wipe.",
        parse_mode="Markdown",
    )


async def _plugins_command(update, context) -> None:
    from tgai_agent.plugins.registry import PluginRegistry
    from tgai_agent.security.permissions import require_permission

    user = update.effective_user
    if not await require_permission(user.id):
        return

    plugins = PluginRegistry.list_all()
    if not plugins:
        await update.message.reply_text("No plugins loaded.")
        return

    lines = ["🔌 *Available Plugins:*\n"]
    for p in plugins:
        safe_marker = "🔒" if not p.is_safe else "✅"
        confirm_marker = " ⚠️ (requires confirmation)" if p.requires_confirmation else ""
        lines.append(f"{safe_marker} `{p.name}` — {p.description}{confirm_marker}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def _status_command(update, context) -> None:
    from tgai_agent.plugins.registry import PluginRegistry
    from tgai_agent.security.permissions import is_admin, require_permission

    user = update.effective_user
    if not await require_permission(user.id):
        return

    plugins = PluginRegistry.list_all()
    admin = await is_admin(user.id)

    text = (
        "📊 *System Status*\n\n"
        f"🤖 Bot: ✅ Online\n"
        f"🔌 Plugins: {len(plugins)} loaded\n"
        f"📋 Scheduler: ✅ Running\n"
        f"👤 Your access: {'🔑 Admin' if admin else '👤 User'}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def _help_command(update, context) -> None:
    text = """
📖 *Help — AI Agent Platform*

*Core Commands:*
/start — Show main menu
/config — Configure AI provider and chat settings
/agents — Manage your AI sub-agents
/tasks — Manage scheduled tasks
/memory — View/clear conversation memory
/plugins — List available plugins
/status — System status
/help — This message

*Quick Tips:*
• Use /config to set your AI provider API key
• Start chatting and I'll respond using AI
• Create agents for specialised tasks (research, coding, writing)
• Schedule tasks to run automatically

*Auto-Reply:*
I'll ask your permission before auto-replying in each chat.
Enable it per-chat via /config → Toggle Auto-Reply.
""".strip()
    await update.message.reply_text(text, parse_mode="Markdown")
