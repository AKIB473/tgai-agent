"""Tests for permission system."""

import pytest


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    from tgai_agent.config import get_settings

    get_settings.cache_clear()
    new_settings = get_settings()
    import tgai_agent.config as cfg
    import tgai_agent.storage.database as db_mod
    import tgai_agent.storage.encryption as enc_mod

    monkeypatch.setattr(cfg, "settings", new_settings)
    monkeypatch.setattr(db_mod, "settings", new_settings)
    monkeypatch.setattr(enc_mod, "settings", new_settings)
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_admin_from_env():
    import tgai_agent.config as cfg

    settings = cfg.settings
    from tgai_agent.security.permissions import PermissionLevel, get_permission_level

    if settings.admin_ids:
        level = await get_permission_level(settings.admin_ids[0])
        assert level == PermissionLevel.ADMIN


@pytest.mark.asyncio
async def test_unknown_user_is_regular_user():
    from tgai_agent.security.permissions import PermissionLevel, get_permission_level
    from tgai_agent.storage.database import init_db

    await init_db()
    assert await get_permission_level(999888777) == PermissionLevel.USER


@pytest.mark.asyncio
async def test_banned_user_is_banned():
    from tgai_agent.security.permissions import PermissionLevel, get_permission_level
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import ban_user, upsert_user

    await init_db()
    await upsert_user(111222333)
    await ban_user(111222333)
    assert await get_permission_level(111222333) == PermissionLevel.BANNED


@pytest.mark.asyncio
async def test_require_permission_false_for_banned():
    from tgai_agent.security.permissions import require_permission
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import ban_user, upsert_user

    await init_db()
    await upsert_user(444555666)
    await ban_user(444555666)
    assert await require_permission(444555666) is False


@pytest.mark.asyncio
async def test_require_permission_true_for_regular():
    from tgai_agent.security.permissions import require_permission
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(555666777)
    assert await require_permission(555666777) is True


@pytest.mark.asyncio
async def test_is_admin_false_for_regular():
    from tgai_agent.security.permissions import is_admin
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(666777888)
    assert await is_admin(666777888) is False


def test_permission_levels_ordering():
    from tgai_agent.security.permissions import PermissionLevel

    assert PermissionLevel.ADMIN > PermissionLevel.USER > PermissionLevel.BANNED
