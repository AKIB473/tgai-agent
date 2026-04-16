# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-16

### Added
- Dual-interface system: Telegram Bot API + optional Telethon user-account mode
- Multi-provider AI layer: OpenAI, Google Gemini, Anthropic Claude
- Per-user encrypted API key storage (AES-256 via Fernet)
- Short-term conversation memory (sliding-window, DB-backed)
- Long-term memory via AI summarisation (auto-compresses when history grows)
- Sub-agent system with role presets (researcher, coder, writer, analyst)
- Sub-agents support tool-use (ReAct-style plugin calling loop)
- Task scheduler: one-shot, interval, and cron triggers (APScheduler)
- Plugin system with auto-discovery from `plugins/builtin/`
- Built-in plugins: web search (DuckDuckGo), URL summariser, sandboxed Python runner
- Per-chat configuration: provider, model, tone, system prompt, auto-reply toggle
- Auto-reply consent flow: asks permission before replying in new chats
- Permission system: USER / ADMIN levels, ban support
- Per-user + per-chat sliding-window rate limiting
- Telethon flood-wait handling and anti-spam throttling
- Structured logging via structlog
- Async retry decorator with exponential back-off
- Interactive inline keyboard menus for all features
- `tgai-agent` CLI entrypoint + `python -m tgai_agent` support
- Full test suite with pytest + pytest-asyncio
- GitHub Actions CI/CD pipeline
- Docker + docker-compose support
- Pre-commit hooks (Black, Ruff, MyPy)
