"""
bot_interface/commands/agents_cmd.py — /agents command.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from tgai_agent.agent_manager.manager import list_user_agents, spawn_agent, stop_agent
from tgai_agent.agent_manager.roles.presets import get_preset, list_presets
from tgai_agent.bot_interface.menus.keyboards import agents_menu, presets_menu
from tgai_agent.security.permissions import require_permission
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not await require_permission(user.id):
        return

    agents = await list_user_agents(user.id)
    if not agents:
        text = (
            "🤖 *Your Agents*\n\n"
            "You have no agents yet.\n"
            "Tap ➕ New Agent to create one!"
        )
    else:
        lines = [f"🤖 *Your Agents* ({len(agents)} total)\n"]
        for a in agents:
            icon = "🟢" if a["state"] == "running" else "⚪"
            lines.append(f"{icon} *{a['name']}* — _{a['role']}_")
        text = "\n".join(lines)

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=agents_menu(agents),
    )


async def handle_new_agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback: user tapped 'New Agent' — show presets."""
    query = update.callback_query
    await query.answer()
    presets = list_presets()
    await query.edit_message_text(
        "🤖 *Choose an agent role:*\n\n"
        "Presets give your agent a pre-configured personality and skills.\n"
        "You can also create a custom agent.",
        parse_mode="Markdown",
        reply_markup=presets_menu(presets),
    )


async def handle_agent_preset(update: Update, context: ContextTypes.DEFAULT_TYPE, preset_name: str) -> None:
    """Create an agent from a preset."""
    query = update.callback_query
    user = query.from_user
    await query.answer()

    preset = get_preset(preset_name)
    if not preset:
        await query.edit_message_text(f"❌ Unknown preset: {preset_name}")
        return

    agent = await spawn_agent(
        user_id=user.id,
        name=f"My {preset_name.title()} Agent",
        role=preset["role"],
        system_prompt=preset["system_prompt"],
        ai_provider="openai",
        ai_model="gpt-4o-mini",
    )
    await query.edit_message_text(
        f"✅ Agent *{agent.name}* created!\n\n"
        f"Role: _{agent.role}_\n"
        f"Provider: `{agent.ai_provider}`\n\n"
        "You can now talk to your agent from the Agents menu.",
        parse_mode="Markdown",
    )
    log.info("agent.created_from_preset", user_id=user.id, agent_id=agent.agent_id)


async def handle_agent_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, agent_id: str) -> None:
    query = update.callback_query
    user = query.from_user
    await query.answer()
    success = await stop_agent(agent_id, user.id)
    if success:
        await query.edit_message_text("✅ Agent deleted.")
    else:
        await query.edit_message_text("❌ Could not delete agent (not found or not yours).")
