"""
Root conftest.py — sets up test environment variables before any imports.
"""

import os

from cryptography.fernet import Fernet

# Must be set BEFORE any tgai_agent imports happen
os.environ.setdefault("BOT_TOKEN", "1234567890:AABBCCDDEEFFaabbccddeeff-1234567890AB")
os.environ.setdefault("API_ID", "12345678")
os.environ.setdefault("API_HASH", "abcdef1234567890abcdef1234567890")
os.environ.setdefault("ADMIN_IDS", "123456789")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())

import pytest


@pytest.fixture(scope="session")
def test_encryption_key():
    return os.environ["ENCRYPTION_KEY"]


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """
    Reset the settings lru_cache before each test so monkeypatched
    env vars (e.g. DB_PATH) are picked up by new Settings instances.
    Also update the module-level `settings` alias used by repositories.
    """
    yield
    # Clean up after test
    try:
        from tgai_agent.config import get_settings

        get_settings.cache_clear()
    except Exception:
        pass
