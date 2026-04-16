"""
config.py — Central configuration loader using Pydantic Settings.
All environment variables are validated on startup; missing required
values raise a clear error rather than failing silently at runtime.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings  # pip: pydantic-settings

load_dotenv()


class Settings(BaseSettings):
    # ── Telegram Bot ─────────────────────────────────────────────────────
    bot_token: str = Field(..., env="BOT_TOKEN")

    # ── Telegram API (Telethon) ───────────────────────────────────────────
    api_id: int = Field(..., env="API_ID")
    api_hash: str = Field(..., env="API_HASH")
    user_mode_enabled: bool = Field(False, env="USER_MODE_ENABLED")
    session_path: str = Field("sessions/", env="SESSION_PATH")

    # ── Security ─────────────────────────────────────────────────────────
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    admin_ids: List[int] = Field(default_factory=list, env="ADMIN_IDS")

    # ── AI Providers (system defaults) ───────────────────────────────────
    openai_api_key: str = Field("", env="OPENAI_API_KEY")
    gemini_api_key: str = Field("", env="GEMINI_API_KEY")
    claude_api_key: str = Field("", env="CLAUDE_API_KEY")

    # ── Storage ──────────────────────────────────────────────────────────
    db_path: str = Field("data.db", env="DB_PATH")

    # ── Logging ──────────────────────────────────────────────────────────
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # ── Rate Limits ──────────────────────────────────────────────────────
    max_requests_per_minute: int = Field(20, env="MAX_REQUESTS_PER_MINUTE")
    max_messages_per_chat_per_minute: int = Field(5, env="MAX_MESSAGES_PER_CHAT_PER_MINUTE")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return upper

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton settings instance."""
    return Settings()


# Convenience alias used throughout the codebase
settings = get_settings()
