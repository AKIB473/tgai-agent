"""
bot_interface/commands/tasks_cmd.py — /tasks command.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from tgai_agent.bot_interface.menus.keyboards import tasks_menu
from tgai_agent.security.permissions import require_permission
from tgai_agent.storage.repositories.task_repo import delete_task, list_tasks
from tgai_agent.task_scheduler.scheduler import scheduler
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not await require_permission(user.id):
        return

    tasks = await list_tasks(user.id, active_only=False)
    if not tasks:
        text = (
            "📋 *Your Tasks*\n\n"
            "No tasks yet. Tap ➕ New Task to schedule one!\n\n"
            "Example tasks:\n"
            "• Send a message at a specific time\n"
            "• Run an agent task every hour\n"
            "• Execute a plugin on a cron schedule"
        )
    else:
        active = sum(1 for t in tasks if t["is_active"])
        lines = [f"📋 *Your Tasks* ({active} active, {len(tasks)} total)\n"]
        for t in tasks:
            icon = "🟢" if t["is_active"] else "⚪"
            trigger = f"{t['trigger_type']}({t['trigger_value'][:20]})"
            lines.append(f"{icon} *{t['name']}* — `{trigger}`")
        text = "\n".join(lines)

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=tasks_menu(tasks),
    )


async def handle_task_delete(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    task_id: str,
) -> None:
    query = update.callback_query
    user = query.from_user
    await query.answer()

    success = await delete_task(task_id, user.id)
    if success:
        scheduler.unschedule_job(task_id)
        await query.edit_message_text("✅ Task deleted.")
    else:
        await query.edit_message_text("❌ Task not found or not yours.")
