"""
task_scheduler/scheduler.py — APScheduler-based async task scheduler.

Supports three trigger types:
  - 'once'     → DateTrigger (ISO timestamp)
  - 'interval' → IntervalTrigger (seconds)
  - 'cron'     → CronTrigger (cron expression)

Tasks are loaded from the DB on startup and re-registered.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from tgai_agent.storage.repositories.task_repo import (
    deactivate_task,
    list_tasks,
    update_task_run,
)
from tgai_agent.task_scheduler.executor import execute_job
from tgai_agent.task_scheduler.job import Job
from tgai_agent.utils.helpers import utcnow
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


class TaskScheduler:
    """
    Wraps APScheduler to provide a clean interface for managing
    user-defined scheduled tasks.
    """

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._bot = None
        self._context: dict = {}

    def set_bot(self, bot, context: dict | None = None) -> None:
        self._bot = bot
        self._context = context or {}

    def start(self) -> None:
        if not self._scheduler.running:
            try:
                self._scheduler.start()
            except (RuntimeError, Exception):
                # Recreate scheduler if the underlying executor was already shut down
                # (can happen in tests where the event loop is replaced between runs)
                self._scheduler = AsyncIOScheduler(timezone="UTC")
                self._scheduler.start()
            log.info("scheduler.started")

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            log.info("scheduler.stopped")

    async def load_from_db(self, user_ids: list[int] | None = None) -> int:
        """
        On startup: load all active tasks from the DB and schedule them.
        Returns count of tasks loaded.
        """
        # Load tasks for all users (use a broad query if no user filter)
        all_tasks: list[dict] = []
        if user_ids:
            for uid in user_ids:
                all_tasks.extend(await list_tasks(uid, active_only=True))

        count = 0
        for row in all_tasks:
            try:
                job = Job.from_db_row(row)
                self.schedule_job(job)
                count += 1
            except Exception as exc:
                log.warning("scheduler.load_failed", task_id=row.get("id"), error=str(exc))

        log.info("scheduler.loaded", count=count)
        return count

    def schedule_job(self, job: Job) -> bool:
        """Add a job to the scheduler. Returns True on success."""
        trigger = self._build_trigger(job)
        if trigger is None:
            return False

        job_id = f"task_{job.id}"
        self._scheduler.add_job(
            self._run_job,
            trigger=trigger,
            id=job_id,
            args=[job],
            replace_existing=True,
            misfire_grace_time=300,
        )
        log.info(
            "scheduler.job_added",
            job_id=job_id,
            trigger=job.trigger_type,
            value=job.trigger_value,
        )
        return True

    def unschedule_job(self, task_id: str) -> None:
        job_id = f"task_{task_id}"
        try:
            self._scheduler.remove_job(job_id)
            log.info("scheduler.job_removed", job_id=job_id)
        except Exception:
            pass

    def _build_trigger(self, job: Job):
        try:
            if job.trigger_type == "once":
                dt = datetime.fromisoformat(job.trigger_value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return DateTrigger(run_date=dt)

            elif job.trigger_type == "interval":
                seconds = int(job.trigger_value)
                return IntervalTrigger(seconds=seconds)

            elif job.trigger_type == "cron":
                return CronTrigger.from_crontab(job.trigger_value, timezone="UTC")

        except Exception as exc:
            log.error(
                "scheduler.trigger_build_failed",
                job_id=job.id,
                trigger_type=job.trigger_type,
                value=job.trigger_value,
                error=str(exc),
            )
            return None

    async def _run_job(self, job: Job) -> None:
        """Internal callback: execute the job and update DB state."""
        try:
            await execute_job(job, self._bot, self._context)
            await update_task_run(job.id)

            # Deactivate one-shot tasks after execution
            if job.trigger_type == "once":
                await deactivate_task(job.id)
                self.unschedule_job(job.id)

        except Exception as exc:
            log.error("scheduler.job_failed", job_id=job.id, error=str(exc))


# Global singleton
scheduler = TaskScheduler()
