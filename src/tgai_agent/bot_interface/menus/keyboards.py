"""
bot_interface/menus/keyboards.py — Reusable inline keyboard layouts.
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤖 Agents", callback_data="menu:agents"),
            InlineKeyboardButton("📋 Tasks", callback_data="menu:tasks"),
        ],
        [
            InlineKeyboardButton("⚙️ Config", callback_data="menu:config"),
            InlineKeyboardButton("🧠 Memory", callback_data="menu:memory"),
        ],
        [
            InlineKeyboardButton("🔌 Plugins", callback_data="menu:plugins"),
            InlineKeyboardButton("📊 Status", callback_data="menu:status"),
        ],
    ])


def config_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Set API Key", callback_data="config:set_key")],
        [InlineKeyboardButton("🤖 Change AI Provider", callback_data="config:provider")],
        [InlineKeyboardButton("💬 Set System Prompt", callback_data="config:prompt")],
        [InlineKeyboardButton("🔄 Toggle Auto-Reply", callback_data="config:autoreply")],
        [InlineKeyboardButton("🎭 Set Tone", callback_data="config:tone")],
        [InlineKeyboardButton("◀️ Back", callback_data="menu:main")],
    ])


def provider_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("OpenAI (GPT)", callback_data="provider:openai")],
        [InlineKeyboardButton("Google Gemini", callback_data="provider:gemini")],
        [InlineKeyboardButton("Anthropic Claude", callback_data="provider:claude")],
        [InlineKeyboardButton("◀️ Back", callback_data="menu:config")],
    ])


def tone_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😊 Casual", callback_data="tone:casual"),
            InlineKeyboardButton("👔 Formal", callback_data="tone:formal"),
        ],
        [
            InlineKeyboardButton("⚖️ Neutral", callback_data="tone:neutral"),
            InlineKeyboardButton("😄 Playful", callback_data="tone:playful"),
        ],
        [InlineKeyboardButton("◀️ Back", callback_data="menu:config")],
    ])


def agents_menu(agents: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for agent in agents[:8]:  # Max 8 shown
        rows.append([
            InlineKeyboardButton(
                f"{'🟢' if agent['state'] == 'running' else '⚪'} {agent['name']}",
                callback_data=f"agent:view:{agent['id']}",
            )
        ])
    rows.append([InlineKeyboardButton("➕ New Agent", callback_data="agent:new")])
    rows.append([InlineKeyboardButton("◀️ Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def agent_action_menu(agent_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Talk to Agent", callback_data=f"agent:talk:{agent_id}")],
        [InlineKeyboardButton("🗑️ Delete Agent", callback_data=f"agent:delete:{agent_id}")],
        [InlineKeyboardButton("◀️ Back", callback_data="menu:agents")],
    ])


def confirm_menu(yes_data: str, no_data: str = "menu:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data=yes_data),
            InlineKeyboardButton("❌ No", callback_data=no_data),
        ]
    ])


def tasks_menu(tasks: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for task in tasks[:8]:
        rows.append([
            InlineKeyboardButton(
                f"{'🟢' if task['is_active'] else '⚪'} {task['name']}",
                callback_data=f"task:view:{task['id']}",
            )
        ])
    rows.append([InlineKeyboardButton("➕ New Task", callback_data="task:new")])
    rows.append([InlineKeyboardButton("◀️ Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def presets_menu(presets: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(p.title(), callback_data=f"agent:preset:{p}")] for p in presets]
    rows.append([InlineKeyboardButton("✏️ Custom", callback_data="agent:custom")])
    rows.append([InlineKeyboardButton("◀️ Back", callback_data="menu:agents")])
    return InlineKeyboardMarkup(rows)


def auto_reply_prompt_menu(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Enable auto-reply", callback_data=f"autoreply:yes:{chat_id}"),
            InlineKeyboardButton("❌ No thanks", callback_data=f"autoreply:no:{chat_id}"),
        ]
    ])
