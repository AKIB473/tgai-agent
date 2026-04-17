"""
main.py — Application entry point.

Startup sequence:
  1. Configure logging
  2. Initialise database
  3. Auto-discover plugins
  4. Build and start the Telegram bot
  5. (Optional) Start Telethon user client if USER_MODE_ENABLED=true
  6. Start the task scheduler and load persisted jobs
  7. Run the event loop until interrupted
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from tgai_agent.config import settings
from tgai_agent.utils.logger import configure_logging, get_logger

log = get_logger(__name__)


async def main() -> None:
    configure_logging(settings.log_level)
    # ── 1. Database ──────────────────────────────────────────────────────
    from tgai_agent.storage.database import init_db

    await init_db()

    # ── 2. Plugins ───────────────────────────────────────────────────────
    from tgai_agent.plugins.registry import PluginRegistry

    PluginRegistry.autodiscover()
    log.info("startup.plugins", count=len(PluginRegistry.list_all()))

    # ── 3. Bot ───────────────────────────────────────────────────────────
    from tgai_agent.bot_interface.bot import build_application

    app = build_application()
    await app.initialize()
    await app.start()
    log.info("startup.bot_started")

    # ── 4. Scheduler ─────────────────────────────────────────────────────
    from tgai_agent.task_scheduler.scheduler import scheduler

    scheduler.set_bot(app)
    scheduler.start()
    # Note: To load tasks for specific users, call scheduler.load_from_db([user_id])
    # For now we skip pre-loading (tasks will be scheduled when created)
    log.info("startup.scheduler_started")

    # ── 5. User client (optional) ─────────────────────────────────────────
    telethon_client = None
    if settings.user_mode_enabled:
        log.info("startup.user_mode_enabled")
        try:
            from tgai_agent.user_client.client import get_client
            from tgai_agent.user_client.event_listeners import register_listeners

            telethon_client = await get_client()

            # Resolve the owner's Telegram user ID
            me = await telethon_client.get_me()
            register_listeners(telethon_client, me.id)
            log.info("startup.telethon_active", user_id=me.id)
        except Exception as exc:
            log.error("startup.telethon_failed", error=str(exc))
            log.warning("startup.continuing_without_user_mode")

    # ── 6. Run ───────────────────────────────────────────────────────────
    log.info("startup.complete", version="1.0.0")
    print("\n🤖 Telegram AI Agent Platform is running. Press Ctrl+C to stop.\n")

    try:
        # Run bot polling + (optional) Telethon in the same event loop
        if telethon_client:
            await asyncio.gather(
                app.updater.start_polling(drop_pending_updates=True),
                telethon_client.run_until_disconnected(),
            )
        else:
            await app.updater.start_polling(drop_pending_updates=True)
            await asyncio.Event().wait()  # Block forever until Ctrl+C
    except (KeyboardInterrupt, SystemExit):
        log.info("shutdown.signal_received")
    finally:
        await _shutdown(app, telethon_client)


async def _shutdown(app, telethon_client) -> None:
    log.info("shutdown.starting")
    from tgai_agent.task_scheduler.scheduler import scheduler

    scheduler.stop()

    if telethon_client:
        from tgai_agent.user_client.client import disconnect_client

        await disconnect_client()

    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    log.info("shutdown.complete")


def init_db_only() -> None:
    """CLI: python main.py --init-db"""

    async def _run():
        configure_logging(settings.log_level)
        from tgai_agent.storage.database import init_db

        await init_db()
        print("✅ Database initialised.")

    asyncio.run(_run())


def cli_entry() -> None:
    """Entrypoint for `tgai-agent` CLI command and `python -m tgai_agent`."""
    parser = argparse.ArgumentParser(
        prog="tgai-agent",
        description="🤖 Telegram AI Agent Platform",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialise the database schema and exit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="tgai-agent 1.0.0",
    )
    args = parser.parse_args()

    configure_logging(settings.log_level)

    if args.init_db:
        init_db_only()
        sys.exit(0)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    cli_entry()
