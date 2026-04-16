"""
user_client/event_listeners.py — Telethon event listeners for user-account mode.

Receives incoming messages for the user account and routes them through
the AI pipeline — but ONLY for chats where the user has explicitly
enabled auto-reply via the bot.
"""

from __future__ import annotations

from telethon import events
from telethon.errors import FloodWaitError

from tgai_agent.ai_core.base_provider import AIMessage
from tgai_agent.ai_core.memory.short_term import ShortTermMemory
from tgai_agent.ai_core.router import complete
from tgai_agent.storage.repositories.chat_repo import get_chat_config
from tgai_agent.user_client.rate_limiter import can_send_to_peer, handle_flood_wait
from tgai_agent.utils.helpers import truncate
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

_owner_user_id: int | None = None


def register_listeners(client, owner_user_id: int) -> None:
    """Attach all event listeners to the Telethon client."""
    global _owner_user_id
    _owner_user_id = owner_user_id

    @client.on(events.NewMessage(incoming=True))
    async def on_new_message(event):
        await _handle_incoming(event)

    log.info("telethon.listeners_registered", owner=owner_user_id)


async def _handle_incoming(event) -> None:
    """Process an incoming message on the user account."""
    if _owner_user_id is None:
        return

    try:
        sender = await event.get_sender()
        if sender is None:
            return

        # Ignore bots and channels
        if getattr(sender, "bot", False):
            return

        chat_id = event.chat_id
        text = event.message.text or ""
        if not text.strip():
            return

        # Check if auto-reply is enabled for this chat
        config = await get_chat_config(_owner_user_id, chat_id)
        if not config.get("auto_reply"):
            return  # Silently ignore — auto-reply not enabled for this chat

        # Rate limit: prevent flooding any single chat
        if not await can_send_to_peer(chat_id):
            return

        log.info(
            "telethon.incoming",
            chat_id=chat_id,
            sender_id=getattr(sender, "id", "?"),
        )

        # Build context + call AI
        memory = ShortTermMemory(_owner_user_id, chat_id)
        user_text = truncate(text, 4000)
        await memory.add("user", user_text)

        system_prompt = config.get("system_prompt", "You are a helpful AI assistant.")
        messages = await memory.get_context(system_prompt=system_prompt)

        try:
            response = await complete(
                _owner_user_id,
                config["ai_provider"],
                messages,
                model=config["ai_model"],
            )
        except Exception as exc:
            log.error("telethon.ai_error", error=str(exc))
            return  # Fail silently — don't send an error message to others

        await memory.add("assistant", response)

        # Send the reply via Telethon (typing simulation for realism)
        async with event.client.action(chat_id, "typing"):
            import asyncio
            # Brief realistic delay (0.5–1.5s based on response length)
            delay = min(0.5 + len(response) / 800, 1.5)
            await asyncio.sleep(delay)

        await event.respond(truncate(response, 4096))
        log.info("telethon.replied", chat_id=chat_id, chars=len(response))

    except FloodWaitError as exc:
        await handle_flood_wait(exc)
    except Exception as exc:
        log.error("telethon.listener_error", error=str(exc))
