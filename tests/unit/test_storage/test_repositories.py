"""Tests for all storage repositories."""

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


# ── User repo ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_and_get_user():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import get_user, upsert_user

    await init_db()
    await upsert_user(12345, username="testuser", first_name="Test")
    user = await get_user(12345)
    assert user is not None
    assert user["username"] == "testuser"
    assert user["first_name"] == "Test"


@pytest.mark.asyncio
async def test_get_nonexistent_user_returns_none():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import get_user

    await init_db()
    user = await get_user(999999999)
    assert user is None


@pytest.mark.asyncio
async def test_upsert_user_twice_updates():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import get_user, upsert_user

    await init_db()
    await upsert_user(99999, username="old", first_name="Old")
    await upsert_user(99999, username="new", first_name="New")
    user = await get_user(99999)
    assert user["username"] == "new"


@pytest.mark.asyncio
async def test_ban_user():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import ban_user, is_banned, upsert_user

    await init_db()
    await upsert_user(11111)
    assert not await is_banned(11111)
    await ban_user(11111)
    assert await is_banned(11111)


@pytest.mark.asyncio
async def test_list_users():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.user_repo import list_users, upsert_user

    await init_db()
    await upsert_user(1001, username="a")
    await upsert_user(1002, username="b")
    users = await list_users()
    ids = [u["id"] for u in users]
    assert 1001 in ids and 1002 in ids


# ── Chat repo ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_chat_config_defaults():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.chat_repo import get_chat_config
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(11111)
    config = await get_chat_config(11111, 22222)
    assert config["ai_provider"] == "openai"
    assert config["ai_model"] == "gpt-4o-mini"
    assert not config["auto_reply"]
    assert config["tone"] == "neutral"


@pytest.mark.asyncio
async def test_upsert_chat_config():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.chat_repo import get_chat_config, upsert_chat_config
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(33333)
    await upsert_chat_config(33333, 44444, ai_provider="claude", tone="formal")
    config = await get_chat_config(33333, 44444)
    assert config["ai_provider"] == "claude"
    assert config["tone"] == "formal"


@pytest.mark.asyncio
async def test_api_key_save_and_get():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.chat_repo import get_api_key, save_api_key
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(55555)
    await save_api_key(55555, "openai", "sk-test-key-12345")
    retrieved = await get_api_key(55555, "openai")
    assert retrieved == "sk-test-key-12345"


@pytest.mark.asyncio
async def test_api_key_overwrite():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.chat_repo import get_api_key, save_api_key
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(66666)
    await save_api_key(66666, "openai", "sk-old")
    await save_api_key(66666, "openai", "sk-new")
    retrieved = await get_api_key(66666, "openai")
    assert retrieved == "sk-new"


@pytest.mark.asyncio
async def test_api_key_missing_returns_empty():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.chat_repo import get_api_key
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(77777)
    key = await get_api_key(77777, "gemini")
    assert key == ""


@pytest.mark.asyncio
async def test_message_append_and_get():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.chat_repo import append_message, get_messages
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(88888)
    await append_message(88888, 99999, "user", "Hello")
    await append_message(88888, 99999, "assistant", "Hi!")
    msgs = await get_messages(88888, 99999)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Hello"
    assert msgs[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_messages_chronological_order():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.chat_repo import append_message, get_messages
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(10001)
    for i in range(5):
        await append_message(10001, 20001, "user", f"msg{i}")
    msgs = await get_messages(10001, 20001)
    assert [m["content"] for m in msgs] == [f"msg{i}" for i in range(5)]


@pytest.mark.asyncio
async def test_clear_messages():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.chat_repo import (
        append_message,
        clear_messages,
        get_messages,
    )
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(10002)
    await append_message(10002, 20002, "user", "a")
    await append_message(10002, 20002, "user", "b")
    count = await clear_messages(10002, 20002)
    assert count == 2
    assert await get_messages(10002, 20002) == []


# ── Task repo ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_create_and_list():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.task_repo import create_task, list_tasks
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(30001)
    task_id = await create_task(
        user_id=30001,
        name="Test Task",
        trigger_type="interval",
        trigger_value="3600",
        action_type="message",
        action_payload={"chat_id": 123, "text": "hello"},
    )
    assert task_id
    tasks = await list_tasks(30001)
    assert len(tasks) == 1
    assert tasks[0]["name"] == "Test Task"


@pytest.mark.asyncio
async def test_task_get():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.task_repo import create_task, get_task
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(30002)
    task_id = await create_task(
        user_id=30002,
        name="Cron Task",
        trigger_type="cron",
        trigger_value="0 9 * * *",
        action_type="message",
        action_payload={"chat_id": 456, "text": "morning!"},
    )
    task = await get_task(task_id)
    assert task is not None
    assert task["name"] == "Cron Task"
    assert task["action_payload"]["text"] == "morning!"


@pytest.mark.asyncio
async def test_task_delete():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.task_repo import create_task, delete_task, list_tasks
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(30003)
    task_id = await create_task(
        user_id=30003,
        name="Delete Me",
        trigger_type="once",
        trigger_value="2030-01-01T00:00:00",
        action_type="message",
        action_payload={"chat_id": 1, "text": "bye"},
    )
    assert await delete_task(task_id, 30003)
    assert await list_tasks(30003, active_only=False) == []


# ── Agent repo ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_agent_create_and_get():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.agent_repo import create_agent, get_agent
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(40001)
    agent_id = await create_agent(
        user_id=40001,
        name="TestAgent",
        role="assistant",
        system_prompt="Be helpful.",
        ai_provider="openai",
        ai_model="gpt-4o-mini",
    )
    agent = await get_agent(agent_id)
    assert agent is not None
    assert agent["name"] == "TestAgent"
    assert agent["state"] == "idle"


@pytest.mark.asyncio
async def test_agent_update_state():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.agent_repo import (
        create_agent,
        get_agent,
        update_agent_state,
    )
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(40002)
    agent_id = await create_agent(
        user_id=40002,
        name="StateAgent",
        role="coder",
        system_prompt="Write code.",
        ai_provider="openai",
        ai_model="gpt-4o-mini",
    )
    await update_agent_state(agent_id, "running")
    assert (await get_agent(agent_id))["state"] == "running"


@pytest.mark.asyncio
async def test_agent_delete():
    from tgai_agent.storage.database import init_db
    from tgai_agent.storage.repositories.agent_repo import create_agent, delete_agent, get_agent
    from tgai_agent.storage.repositories.user_repo import upsert_user

    await init_db()
    await upsert_user(40003)
    agent_id = await create_agent(
        user_id=40003,
        name="Deletable",
        role="writer",
        system_prompt="Write.",
        ai_provider="gemini",
        ai_model="gemini-1.5-flash",
    )
    assert await delete_agent(agent_id, 40003)
    assert await get_agent(agent_id) is None
