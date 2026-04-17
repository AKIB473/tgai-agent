"""
bot_interface/handlers/callback_handler.py — Central inline button callback router.

All CallbackQuery events are dispatched here and routed by prefix.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from tgai_agent.agent_manager.manager import list_user_agents, talk_to_agent
from tgai_agent.bot_interface.commands.agents_cmd import (
    handle_agent_delete,
    handle_agent_preset,
    handle_new_agent,
)
from tgai_agent.bot_interface.commands.config_cmd import (
    handle_set_api_key_prompt,
    handle_set_prompt,
)
from tgai_agent.bot_interface.commands.tasks_cmd import handle_task_delete
from tgai_agent.bot_interface.menus.keyboards import (
    agent_action_menu,
    agents_menu,
    config_menu,
    confirm_menu,
    main_menu,
    provider_menu,
    tasks_menu,
    tone_menu,
)
from tgai_agent.security.permissions import require_permission
from tgai_agent.storage.repositories.chat_repo import upsert_chat_config
from tgai_agent.storage.repositories.task_repo import list_tasks
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    data = query.data or ""

    if not await require_permission(user.id):
        await query.answer("Access denied.", show_alert=True)
        return

    await query.answer()

    # ── Menu navigation ──────────────────────────────────────────────────
    if data == "menu:main":
        await query.edit_message_text(
            "🏠 *Main Menu* — choose an option:",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )

    elif data == "menu:config":
        await query.edit_message_text(
            "⚙️ *Configuration*",
            parse_mode="Markdown",
            reply_markup=config_menu(),
        )

    elif data == "menu:agents":
        agents = await list_user_agents(user.id)
        await query.edit_message_text(
            f"🤖 *Agents* ({len(agents)} total)",
            parse_mode="Markdown",
            reply_markup=agents_menu(agents),
        )

    elif data == "menu:tasks":
        tasks = await list_tasks(user.id, active_only=False)
        await query.edit_message_text(
            f"📋 *Tasks* ({len(tasks)} total)",
            parse_mode="Markdown",
            reply_markup=tasks_menu(tasks),
        )

    elif data == "menu:status":
        await _handle_status(query, context)

    elif data == "menu:memory":
        chat_id = query.message.chat_id
        from tgai_agent.ai_core.memory.short_term import ShortTermMemory

        memory = ShortTermMemory(user.id, chat_id)
        summary = await memory.summary()
        await query.edit_message_text(
            f"🧠 *Memory*\n\n{summary}\n\nUse /memory clear to wipe.",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )

    elif data == "menu:plugins":
        from tgai_agent.plugins.registry import PluginRegistry

        plugins_list = PluginRegistry.list_all()
        lines = ["🔌 *Available Plugins:*\n"]
        for p in plugins_list:
            safe_marker = "✅" if p.is_safe else "🔒"
            confirm_marker = " ⚠️" if p.requires_confirmation else ""
            lines.append(f"{safe_marker} `{p.name}` — {p.description}{confirm_marker}")
        text = "\n".join(lines) if len(lines) > 1 else "No plugins loaded."
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )

    # ── Config actions ───────────────────────────────────────────────────
    elif data == "config:set_key":
        await handle_set_api_key_prompt(update, context)
        return  # ConversationHandler takes over

    elif data == "config:prompt":
        await handle_set_prompt(update, context)
        return

    elif data == "config:provider":
        await query.edit_message_text(
            "🤖 *Choose AI Provider:*",
            parse_mode="Markdown",
            reply_markup=provider_menu(),
        )

    elif data.startswith("provider:"):
        provider = data.split(":")[1]
        chat_id = query.message.chat_id
        await upsert_chat_config(user.id, chat_id, ai_provider=provider)
        await query.edit_message_text(
            f"✅ Provider changed to *{provider}*",
            parse_mode="Markdown",
            reply_markup=config_menu(),
        )

    elif data == "config:tone":
        await query.edit_message_text(
            "🎭 *Choose tone:*",
            parse_mode="Markdown",
            reply_markup=tone_menu(),
        )

    elif data.startswith("tone:"):
        tone = data.split(":")[1]
        chat_id = query.message.chat_id
        await upsert_chat_config(user.id, chat_id, tone=tone)
        await query.edit_message_text(
            f"✅ Tone set to *{tone}*",
            parse_mode="Markdown",
            reply_markup=config_menu(),
        )

    elif data == "config:autoreply":
        chat_id = query.message.chat_id
        from tgai_agent.storage.repositories.chat_repo import get_chat_config

        current = await get_chat_config(user.id, chat_id)
        new_val = not current.get("auto_reply", False)
        await upsert_chat_config(user.id, chat_id, auto_reply=new_val)
        state = "✅ enabled" if new_val else "❌ disabled"
        await query.edit_message_text(
            f"Auto-reply {state} for this chat.",
            reply_markup=config_menu(),
        )

    # ── Auto-reply consent ───────────────────────────────────────────────
    elif data.startswith("autoreply:"):
        _, decision, chat_id_str = data.split(":")
        chat_id = int(chat_id_str)
        enabled = decision == "yes"
        await upsert_chat_config(user.id, chat_id, auto_reply=enabled, reply_confirmed=True)
        if enabled:
            await query.edit_message_text("✅ Auto-reply enabled for this chat!")
        else:
            await query.edit_message_text("Got it — I'll stay quiet unless you ask.")

    # ── Agent actions ────────────────────────────────────────────────────
    elif data == "agent:new":
        await handle_new_agent(update, context)

    elif data.startswith("agent:view:"):
        agent_id = data.split(":")[2]
        from tgai_agent.storage.repositories.agent_repo import get_agent

        agent_data = await get_agent(agent_id)
        if not agent_data or agent_data["user_id"] != user.id:
            await query.edit_message_text("❌ Agent not found.")
            return
        state_icon = "🟢" if agent_data["state"] == "running" else "⚪"
        text = (
            f"{state_icon} *{agent_data['name']}*\n\n"
            f"Role: _{agent_data['role']}_\n"
            f"Provider: `{agent_data['ai_provider']}` / `{agent_data['ai_model']}`\n"
            f"State: `{agent_data['state']}`\n"
            f"Created: {agent_data['created_at'][:10]}\n"
        )
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=agent_action_menu(agent_id),
        )

    elif data.startswith("agent:preset:"):
        preset = data.split(":")[2]
        await handle_agent_preset(update, context, preset)

    elif data.startswith("agent:delete:"):
        agent_id = data.split(":")[2]
        await handle_agent_delete(update, context, agent_id)

    elif data.startswith("agent:talk:"):
        agent_id = data.split(":")[2]
        context.user_data["talking_to_agent"] = agent_id
        await query.edit_message_text(
            "💬 You're now chatting with your agent.\n"
            "Just send any message and I'll route it to the agent.\n"
            "Send /done to stop talking to the agent."
        )

    # ── Task actions ─────────────────────────────────────────────────────
    elif data.startswith("task:delete:"):
        task_id = data.split(":")[2]
        await handle_task_delete(update, context, task_id)

    elif data == "task:new":
        await query.edit_message_text(
            "📋 *New Task*\n\n"
            "Task creation wizard coming soon.\n\n"
            "For now, tasks can be created programmatically via the API.",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )

    elif data.startswith("task:view:"):
        task_id = data.split(":")[2]
        from tgai_agent.storage.repositories.task_repo import get_task

        task_data = await get_task(task_id)
        if not task_data or task_data["user_id"] != user.id:
            await query.edit_message_text("❌ Task not found.")
            return
        icon = "🟢" if task_data["is_active"] else "⚪"
        text = (
            f"{icon} *{task_data['name']}*\n\n"
            f"Trigger: `{task_data['trigger_type']}` — `{task_data['trigger_value']}`\n"
            f"Action: `{task_data['action_type']}`\n"
            f"Runs: {task_data['run_count']}\n"
            f"Last run: {task_data.get('last_run_at') or 'Never'}\n"
            f"Description: {task_data.get('description') or '—'}\n"
        )
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=confirm_menu(f"task:delete:{task_id}", "menu:tasks"),
        )

    else:
        log.warning("callback.unhandled", data=data)
        await query.answer("Unhandled action.", show_alert=True)


async def _handle_status(query, context) -> None:
    from tgai_agent.plugins.registry import PluginRegistry

    plugins = PluginRegistry.list_all()
    text = (
        "📊 *System Status*\n\n"
        f"🔌 Plugins loaded: {len(plugins)}\n"
        f"Plugins: {', '.join(p.name for p in plugins)}\n\n"
        "✅ Bot: Online\n"
        "✅ Scheduler: Running\n"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())
