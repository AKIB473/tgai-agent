"""Tests for ShortTermMemory and LongTermMemory."""

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
async def test_short_term_add_and_get():
    from tgai_agent.ai_core.memory.short_term import ShortTermMemory
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(1)
    mem = ShortTermMemory(user_id=1, chat_id=100)
    await mem.add("user", "Hello")
    await mem.add("assistant", "Hi there!")
    messages = await mem.get_context()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hello"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Hi there!"


@pytest.mark.asyncio
async def test_short_term_with_system_prompt():
    from tgai_agent.ai_core.memory.short_term import ShortTermMemory
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(2)
    mem = ShortTermMemory(user_id=2, chat_id=200)
    await mem.add("user", "Test message")
    messages = await mem.get_context(system_prompt="Be helpful.")
    assert messages[0].role == "system"
    assert messages[0].content == "Be helpful."
    assert messages[1].role == "user"
    assert messages[1].content == "Test message"


@pytest.mark.asyncio
async def test_short_term_clear():
    from tgai_agent.ai_core.memory.short_term import ShortTermMemory
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(3)
    mem = ShortTermMemory(user_id=3, chat_id=300)
    await mem.add("user", "msg1")
    await mem.add("user", "msg2")
    count = await mem.clear()
    assert count == 2
    messages = await mem.get_context()
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_short_term_window_limit():
    from tgai_agent.ai_core.memory.short_term import ShortTermMemory
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(4)
    mem = ShortTermMemory(user_id=4, chat_id=400, window=3)
    for i in range(10):
        await mem.add("user", f"msg {i}")
    messages = await mem.get_context()
    assert len(messages) == 3
    assert messages[-1].content == "msg 9"


@pytest.mark.asyncio
async def test_short_term_summary():
    from tgai_agent.ai_core.memory.short_term import ShortTermMemory
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(5)
    mem = ShortTermMemory(user_id=5, chat_id=500)
    await mem.add("user", "test")
    summary = await mem.summary()
    assert "1 messages" in summary
    assert "window=" in summary


@pytest.mark.asyncio
async def test_short_term_empty_memory():
    from tgai_agent.ai_core.memory.short_term import ShortTermMemory
    from tgai_agent.storage.database import init_db

    await init_db()
    mem = ShortTermMemory(user_id=6, chat_id=600)
    messages = await mem.get_context()
    assert messages == []


@pytest.mark.asyncio
async def test_short_term_max_window_cap():
    from tgai_agent.ai_core.memory.short_term import MAX_WINDOW, ShortTermMemory

    mem = ShortTermMemory(user_id=7, chat_id=700, window=9999)
    assert mem.window == MAX_WINDOW


@pytest.mark.asyncio
async def test_long_term_no_compress_below_threshold():
    from tgai_agent.ai_core.memory.long_term import LongTermMemory
    from tgai_agent.storage.database import init_db

    await init_db()
    lt = LongTermMemory(user_id=10, chat_id=1000)
    result = await lt.maybe_compress()
    assert result is False
