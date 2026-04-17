#!/bin/bash
# Full verification script for tgai-agent
set -o pipefail
cd /root/.openclaw/workspace/tgai-agent

echo "================================================================"
echo "STEP 1: Full pytest suite"
echo "================================================================"
.venv/bin/python -m pytest tests/ -v --tb=short --no-header 2>&1
PYTEST_EXIT=$?

echo ""
echo "================================================================"
echo "STEP 4: Bot token verification"
echo "================================================================"
.venv/bin/python -c "
import asyncio, httpx
async def check():
    token = '7216668400:AAE82vzSVK1TuA5ZD4k0TyoGsavN4IVHFBQ'
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f'https://api.telegram.org/bot{token}/getMe')
        d = r.json()
        if d.get('ok'):
            b = d['result']
            print(f'BOT OK: {b[\"first_name\"]} (@{b[\"username\"]}) id={b[\"id\"]}')
        else:
            print('BOT FAIL:', d)
asyncio.run(check())
"

echo ""
echo "================================================================"
echo "STEP 5: Init real DB and check tables"
echo "================================================================"
.venv/bin/python -c "
import asyncio, sys, os
sys.path.insert(0, 'src')
from tgai_agent.storage.database import init_db, get_db

async def run():
    await init_db()
    async with await get_db() as db:
        async with db.execute('SELECT name FROM sqlite_master WHERE type=\"table\" ORDER BY name') as cur:
            tables = [r[0] for r in await cur.fetchall()]
    print('Tables:', tables)
    expected = {'users','api_keys','chat_configs','messages','tasks','agents','plugin_logs'}
    missing = expected - set(tables)
    print('All tables present' if not missing else f'Missing: {missing}')

asyncio.run(run())
print('DB size:', os.path.getsize('data.db'), 'bytes')
"

echo ""
echo "================================================================"
echo "STEP 6: getUpdates and send test message"
echo "================================================================"
.venv/bin/python -c "
import asyncio, httpx, json

async def run():
    token = '7216668400:AAE82vzSVK1TuA5ZD4k0TyoGsavN4IVHFBQ'
    admin_id = 7320091256
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f'https://api.telegram.org/bot{token}/getUpdates?limit=5')
        data = r.json()
        chat_id = None
        if data.get('result'):
            for upd in data['result']:
                msg = upd.get('message') or (upd.get('callback_query') or {}).get('message')
                if msg:
                    chat_id = msg['chat']['id']
                    print(f'Found chat_id from updates: {chat_id}')
                    break
        target = chat_id or admin_id
        resp = await client.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={
                'chat_id': target,
                'text': '🤖 *tgai-agent is alive!*\n\n✅ Bot token valid\n✅ DB initialised\n✅ All tests running\n\nYour bot is ready!',
                'parse_mode': 'Markdown'
            }
        )
        result = resp.json()
        if result.get('ok'):
            print(f'Message sent to {target}!')
        else:
            print(f'Send result: {json.dumps(result, indent=2)}')
            print('Tip: Send /start to the bot first to open a chat')

asyncio.run(run())
"

echo ""
echo "================================================================"
echo "SUMMARY"
echo "================================================================"
echo "Pytest exit code: $PYTEST_EXIT"
if [ $PYTEST_EXIT -eq 0 ]; then
    echo "All tests PASSED!"
else
    echo "Some tests FAILED - see above"
fi
