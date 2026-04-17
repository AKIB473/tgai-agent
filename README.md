# 🤖 tgai-agent

**Production-grade AI-powered Telegram agent platform.**

[![CI](https://github.com/AKIB473/tgai-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/AKIB473/tgai-agent/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-207%20passing-brightgreen.svg)](tests/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## What is it?

`tgai-agent` is a modular, async Python framework that turns Telegram into an AI automation platform. It supports **Bot API mode** for standard bot interaction and **optional Telethon user-account mode** for advanced personal automation — both backed by a shared AI layer, memory system, task scheduler, and plugin engine.

---

## Features

| Category | Capability |
|---|---|
| **AI Providers** | OpenAI, Google Gemini, Anthropic Claude — switchable per chat |
| **Memory** | Short-term (DB-backed sliding window) + long-term (AI summarisation) |
| **Sub-agents** | Autonomous agents with 8 role presets, memory, and tool-use (ReAct loop, 10 iterations) |
| **Task Scheduler** | One-shot, interval, and cron triggers via APScheduler |
| **Plugin System** | Auto-discovered; built-ins: web search, URL summariser, sandboxed Python runner |
| **Bot Interface** | Inline keyboard menus, conversation flows, all major commands |
| **User Mode** | Optional Telethon integration for user-account automation |
| **Security** | AES-256 key encryption, per-user rate limiting, permission levels, ban system |
| **Developer DX** | `src/` layout, full type hints, structlog, retry decorator, pre-commit, Docker, 174 tests |

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/AKIB473/tgai-agent
cd tgai-agent
pip install -e ".[dev]"
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
BOT_TOKEN=your_bot_token_from_BotFather
API_ID=12345678
API_HASH=your_api_hash_from_my_telegram_org
ENCRYPTION_KEY=<generate below>
ADMIN_IDS=your_telegram_user_id
```

Generate an encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Initialise Database

```bash
python -m tgai_agent.main --init-db
# or
make init-db
```

### 4. Run

```bash
# Simple start
python run_bot.py

# Or with the single-instance script (kills old instances first)
bash start_once.sh

# Or with Docker
docker-compose up -d
```

---

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Onboarding and main menu |
| `/config` | Set AI provider, API key, tone, system prompt, auto-reply |
| `/agents` | Create and manage AI sub-agents |
| `/tasks` | Schedule one-shot, interval, or cron tasks |
| `/memory` | View or clear conversation memory |
| `/plugins` | List available plugins |
| `/status` | System health overview |
| `/help` | Full command reference |

---

## Architecture

```
src/tgai_agent/
├── main.py                    # Entry point + CLI
├── config.py                  # Pydantic Settings
│
├── bot_interface/             # python-telegram-bot layer
│   ├── bot.py                 # Application builder + handler wiring
│   ├── commands/              # /start, /config, /agents, /tasks
│   ├── handlers/              # Message + callback routing
│   └── menus/keyboards.py     # All inline keyboard layouts
│
├── user_client/               # Telethon user-account layer (opt-in)
│   ├── client.py              # Session management
│   ├── event_listeners.py     # Incoming message hooks
│   └── rate_limiter.py        # Flood-wait + anti-spam
│
├── ai_core/                   # Provider-agnostic AI layer
│   ├── base_provider.py       # Abstract interface
│   ├── router.py              # Dynamic provider/key resolution
│   ├── providers/             # OpenAI, Gemini, Claude
│   └── memory/                # Short-term + long-term memory
│
├── agent_manager/             # Sub-agent lifecycle
│   ├── agent.py               # Agent class (think + run_task)
│   ├── manager.py             # Spawn / stop / talk
│   └── roles/presets.py       # Built-in role templates
│
├── task_scheduler/            # APScheduler wrapper
│   ├── scheduler.py           # Singleton scheduler
│   ├── job.py                 # Job data model
│   └── executor.py            # Job dispatch logic
│
├── plugins/                   # Extensible tool system
│   ├── base_plugin.py         # BasePlugin ABC
│   ├── registry.py            # Auto-discovery + audit logging
│   └── builtin/               # web_search, summarizer, code_runner
│
├── storage/                   # Persistence layer
│   ├── database.py            # SQLite init + WAL mode
│   ├── encryption.py          # Fernet AES-256
│   └── repositories/          # user, chat, task, agent repos
│
├── security/                  # Access control
│   ├── permissions.py         # USER / ADMIN / BANNED levels
│   └── rate_guard.py          # Sliding-window rate limiter
│
└── utils/                     # Shared utilities
    ├── logger.py              # structlog configuration
    ├── retry.py               # Async exponential back-off decorator
    └── helpers.py             # truncate, parse_duration, etc.
```

---

## Writing a Plugin

Drop a file in `src/tgai_agent/plugins/builtin/` — it auto-registers at startup.

```python
from tgai_agent.plugins.base_plugin import BasePlugin, PluginError
from tgai_agent.plugins.registry import PluginRegistry

class WeatherPlugin(BasePlugin):
    name = "get_weather"
    description = "Get current weather for a city"
    parameter_schema = {
        "type": "object",
        "required": ["city"],
        "properties": {"city": {"type": "string"}},
    }

    async def execute(self, params: dict, context: dict) -> str:
        city = params.get("city", "").strip()
        if not city:
            raise PluginError("City is required.")
        return f"🌤 Weather in {city}: 22°C, partly cloudy"

PluginRegistry.register(WeatherPlugin())
```

---

## Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | — | Telegram bot token |
| `API_ID` | ✅ | — | Telegram API ID |
| `API_HASH` | ✅ | — | Telegram API hash |
| `ENCRYPTION_KEY` | ✅ | — | Fernet key (32-byte base64) |
| `ADMIN_IDS` | ✅ | — | Comma-separated admin user IDs |
| `OPENAI_API_KEY` | optional | — | System-level OpenAI key |
| `GEMINI_API_KEY` | optional | — | System-level Gemini key |
| `CLAUDE_API_KEY` | optional | — | System-level Claude key |
| `DB_PATH` | optional | `data.db` | SQLite file path |
| `SESSION_PATH` | optional | `sessions/` | Telethon session directory |
| `LOG_LEVEL` | optional | `INFO` | Logging level |
| `USER_MODE_ENABLED` | optional | `false` | Enable Telethon user mode |
| `MAX_REQUESTS_PER_MINUTE` | optional | `20` | Global rate limit per user |
| `MAX_MESSAGES_PER_CHAT_PER_MINUTE` | optional | `5` | Per-chat rate limit |

---

## Development

```bash
# Install with dev extras
pip install -e ".[dev]"

# Run tests (207 tests, all passing)
make test

# Coverage report
make cov

# Lint + format
make lint
make fmt

# Start bot (single instance, kills old ones)
bash start_once.sh

# Or direct
python run_bot.py
```

---

## Test Coverage

```
207 tests across 16 test files:
├── test_ai_core/
│   ├── test_providers.py     # OpenAI, Gemini, Claude (mocked)
│   ├── test_memory.py        # ShortTermMemory, LongTermMemory
│   └── test_router.py        # Provider routing
├── test_agent/
│   ├── test_agent.py         # SubAgent think/run_task/state/last_active
│   └── test_presets.py       # All 8 role presets, get_preset, list_presets
├── test_plugins/
│   ├── test_web_search.py    # WebSearchPlugin (mocked httpx)
│   └── test_code_runner.py   # Sandboxed Python execution
├── test_security/
│   ├── test_permissions.py   # Permission levels, ban system
│   └── test_rate_guard.py    # Sliding-window rate limiting
├── test_storage/
│   ├── test_repositories.py  # All CRUD operations
│   ├── test_encryption_roundtrip.py
│   ├── test_helpers.py
│   └── test_task_scheduler.py
└── test_utils/
    └── test_helpers_extended.py
```

---

## Deployment

### Docker (recommended)

```bash
docker build -t tgai-agent .
docker-compose up -d
docker-compose logs -f
```

### Systemd (Linux VPS)

```ini
[Unit]
Description=Telegram AI Agent
After=network.target

[Service]
User=root
WorkingDirectory=/root/tgai-agent
ExecStart=/root/tgai-agent/.venv/bin/python run_bot.py
Restart=always
RestartSec=5
EnvironmentFile=/root/tgai-agent/.env

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable --now tgai-agent
```

---

## Security Notes

- API keys are encrypted with AES-256 (Fernet) before storage — never stored in plaintext
- User messages containing API keys are deleted from Telegram immediately after capture
- Sandboxed code execution uses RestrictedPython — no OS, filesystem, or network access
- Telethon user mode is **disabled by default** — opt in via `USER_MODE_ENABLED=true`
- Rate limiting prevents abuse; admins can ban users via the permission system
- Sessions directory should have `chmod 700` on production servers

---

## License

[MIT](LICENSE) © 2026 tgai-agent contributors
