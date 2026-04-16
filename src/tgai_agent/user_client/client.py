"""
user_client/client.py — Telethon user-account session management.

⚠️  IMPORTANT SAFETY NOTES:
  - User mode is DISABLED by default (USER_MODE_ENABLED=false in .env)
  - Requires explicit opt-in by the operator
  - Sessions are stored locally (encrypted filesystem recommended)
  - Never use this to spam or automate in ways that violate Telegram ToS
  - Flood-wait handling is mandatory; never bypass it
  - Always throttle automated sends aggressively
"""

from __future__ import annotations

import os
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession

from tgai_agent.config import settings
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

_client_instance: TelegramClient | None = None


def get_session_path(session_name: str = "main") -> str:
    path = Path(settings.session_path)
    path.mkdir(parents=True, exist_ok=True)
    return str(path / session_name)


async def get_client(session_name: str = "main") -> TelegramClient:
    """
    Return a connected Telethon client, creating a new session if needed.

    On first run, Telethon will prompt for phone number + OTP in the terminal.
    Subsequent runs use the saved session file.
    """
    global _client_instance

    if _client_instance and _client_instance.is_connected():
        return _client_instance

    session_file = get_session_path(session_name)
    log.info("telethon.connecting", session=session_file)

    client = TelegramClient(
        session_file,
        settings.api_id,
        settings.api_hash,
        device_model="TelegramAIAgent",
        app_version="1.0.0",
        system_version="Linux",
        lang_code="en",
        # Conservative connection settings
        connection_retries=3,
        retry_delay=5,
        auto_reconnect=True,
        flood_sleep_threshold=60,  # Auto-sleep on flood waits up to 60s
    )

    await client.start()
    _client_instance = client

    me = await client.get_me()
    log.info("telethon.connected", user=f"{me.first_name} (@{me.username})")
    return client


async def disconnect_client() -> None:
    global _client_instance
    if _client_instance and _client_instance.is_connected():
        await _client_instance.disconnect()
        _client_instance = None
        log.info("telethon.disconnected")


async def is_connected() -> bool:
    return _client_instance is not None and _client_instance.is_connected()
