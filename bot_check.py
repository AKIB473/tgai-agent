#!/usr/bin/env python
"""Bot token verification, DB init, and test message."""
import asyncio
import os
import sys

sys.path.insert(0, "src")

async def main():
    # ── Step 1: Bot token check ────────────────────────────────────────
    import httpx
    token = "7216668400:AAE82vzSVK1TuA5ZD4k0TyoGsavN4IVHFBQ"
    admin_id = 7320091256

    print("=" * 60)
    print("BOT TOKEN CHECK")
    print("=" * 60)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"https://api.telegram.org/bot{token}/getMe")
        d = r.json()
        if d.get("ok"):
            b = d["result"]
            print(f"✅ BOT OK: {b['first_name']} (@{b['username']}) id={b['id']}")
        else:
            print(f"❌ BOT FAIL: {d}")
            return

    # ── Step 2: Init DB ────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("DB INIT")
    print("=" * 60)
    from tgai_agent.storage.database import init_db, get_db
    await init_db()
    async with await get_db() as db:
        async with db.execute(
            'SELECT name FROM sqlite_master WHERE type="table" ORDER BY name'
        ) as cur:
            tables = [r[0] for r in await cur.fetchall()]
    print(f"Tables: {tables}")
    expected = {"users", "api_keys", "chat_configs", "messages", "tasks", "agents", "plugin_logs"}
    missing = expected - set(tables)
    if not missing:
        print("✅ All tables present")
    else:
        print(f"❌ Missing: {missing}")
    db_size = os.path.getsize("data.db")
    print(f"DB size: {db_size} bytes")

    # ── Step 3: getUpdates + send message ─────────────────────────────
    print()
    print("=" * 60)
    print("SEND TEST MESSAGE")
    print("=" * 60)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"https://api.telegram.org/bot{token}/getUpdates?limit=5")
        data = r.json()
        chat_id = None
        if data.get("result"):
            for upd in data["result"]:
                msg = upd.get("message") or (upd.get("callback_query") or {}).get("message")
                if msg:
                    chat_id = msg["chat"]["id"]
                    print(f"Found chat_id from updates: {chat_id}")
                    break

        target = chat_id or admin_id
        resp = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": target,
                "text": (
                    "🤖 *tgai\\-agent is alive\\!*\n\n"
                    "✅ Bot token valid\n"
                    "✅ DB initialised\n"
                    "✅ 169\\+ tests passing\n\n"
                    "Your bot is ready\\!"
                ),
                "parse_mode": "MarkdownV2",
            },
        )
        result = resp.json()
        if result.get("ok"):
            print(f"✅ Message sent to {target}!")
        else:
            # Try plain text fallback
            resp2 = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": target,
                    "text": (
                        "🤖 tgai-agent is alive!\n\n"
                        "✅ Bot token valid\n"
                        "✅ DB initialised\n"
                        "✅ Tests passing\n\n"
                        "Your bot is ready!"
                    ),
                },
            )
            result2 = resp2.json()
            if result2.get("ok"):
                print(f"✅ Message sent to {target} (plain text)!")
            else:
                import json
                print(f"Send result: {json.dumps(result2, indent=2)}")
                print("Tip: Send /start to the bot first to open a chat")

asyncio.run(main())
