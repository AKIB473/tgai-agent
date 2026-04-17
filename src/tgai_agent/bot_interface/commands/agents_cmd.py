"""
bot_interface/commands/agents_cmd.py — /agents command with creation wizard.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tgai_agent.agent_manager.manager import list_user_agents, spawn_agent, stop_agent
from tgai_agent.agent_manager.roles.presets import (
    AGENT_PRESETS,
    get_preset,
    get_preset_display,
    list_presets,
)
from tgai_agent.bot_interface.menus.keyboards import agents_menu, presets_menu
from tgai_agent.security.permissions import require_permission
from tgai_agent.utils.helpers import truncate
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

# Conversation states for agent creation wizard
AGENT_WIZARD_NAME = 10
AGENT_WIZARD_PROMPT = 11
AGENT_WIZARD_PROVIDER = 12


async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not await require_permission(user.id):
        return

    agents = await list_user_agents(user.id)
    if not agents:
        text = (
            "🤖 *Your Agents*\n\n"
            "You have no agents yet.\n\n"
            "Agents are specialised AI assistants you can create for specific tasks:\n"
            "• 🔬 Researcher — finds and synthesises information\n"
            "• 💻 Coder — writes and debugs code\n"
            "• ✍️ Writer — writes and edits text\n"
            "• 📊 Analyst — analyses data\n"
            "• 🌍 Translator — translates between languages\n"
            "• 📋 Summarizer — summarises articles and URLs\n"
            "• 🎓 Tutor — teaches any subject\n\n"
            "Tap *➕ New Agent* to create one!"
        )
    else:
        lines = [f"🤖 *Your Agents* ({len(agents)} total)\n"]
        for a in agents:
            preset = AGENT_PRESETS.get(a["role"], {})
            emoji = preset.get("emoji", "🤖")
            desc = preset.get("description", a["role"])
            state_icon = "🟢" if a["state"] == "running" else "⚪"
            lines.append(f"{state_icon} {emoji} *{a['name']}*\n   _{desc}_")
        text = "\n\n".join(lines)

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=agents_menu(agents),
    )


async def handle_new_agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback: user tapped 'New Agent' — show presets menu."""
    query = update.callback_query
    await query.answer()
    presets = list_presets()

    lines = ["🤖 *Choose an agent role:*\n"]
    for role in presets:
        preset = AGENT_PRESETS[role]
        lines.append(f"{preset['emoji']} *{role.title()}* — _{preset['description']}_")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=presets_menu(presets),
    )


async def handle_agent_preset(
    update: Update, context: ContextTypes.DEFAULT_TYPE, preset_name: str
) -> None:
    """Create an agent from a preset."""
    query = update.callback_query
    user = query.from_user
    await query.answer()

    preset = get_preset(preset_name)
    if not preset:
        await query.edit_message_text(f"❌ Unknown preset: {preset_name}")
        return

    # Use the user's current chat config provider
    from tgai_agent.storage.repositories.chat_repo import get_chat_config

    config = await get_chat_config(user.id, query.message.chat_id)
    provider = config.get("ai_provider", "openai")
    model = config.get("ai_model", "gpt-4o-mini")

    emoji = preset.get("emoji", "🤖")
    agent = await spawn_agent(
        user_id=user.id,
        name=f"{emoji} {preset_name.title()} Agent",
        role=preset["role"],
        system_prompt=preset["system_prompt"],
        ai_provider=provider,
        ai_model=model,
    )

    await query.edit_message_text(
        f"✅ *{agent.name}* created!\n\n"
        f"Role: _{preset.get('description', preset['role'])}_\n"
        f"Provider: `{provider}` / `{model}`\n\n"
        "💬 Tap *Talk to Agent* from the Agents menu to start chatting.\n"
        "🔧 The agent will use your configured AI provider and key.",
        parse_mode="Markdown",
    )
    log.info("agent.created_from_preset", user_id=user.id, agent_id=agent.agent_id)


async def handle_agent_delete(
    update: Update, context: ContextTypes.DEFAULT_TYPE, agent_id: str
) -> None:
    query = update.callback_query
    user = query.from_user
    await query.answer()
    success = await stop_agent(agent_id, user.id)
    if success:
        await query.edit_message_text("✅ Agent deleted and memory cleared.")
    else:
        await query.edit_message_text("❌ Could not delete agent (not found or not yours).")


async def handle_agent_run_task(
    update: Update, context: ContextTypes.DEFAULT_TYPE, agent_id: str
) -> None:
    """Run a task with an agent — expects task in user_data."""
    query = update.callback_query
    user = query.from_user
    await query.answer()

    task = context.user_data.get("agent_task", "")
    if not task:
        await query.edit_message_text("❌ No task specified.")
        return

    from tgai_agent.agent_manager.manager import get_live_agent

    agent = await get_live_agent(agent_id)
    if not agent or agent.user_id != user.id:
        await query.edit_message_text("❌ Agent not found.")
        return

    await query.edit_message_text(f"⚙️ Running task with *{agent.name}*...", parse_mode="Markdown")
    result = await agent.run_task(task, {"user_id": user.id, "chat_id": query.message.chat_id})
    await query.message.reply_text(
        f"✅ *{agent.name}* completed the task:\n\n{truncate(result, 3000)}",
        parse_mode="Markdown",
    )
