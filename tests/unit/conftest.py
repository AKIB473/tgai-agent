"""
Unit test conftest — isolates the APScheduler singleton between tests
and prevents 'threads can only be started once' errors.
"""
import pytest


@pytest.fixture(autouse=True)
def reset_scheduler():
    """
    Replace the global scheduler singleton with a fresh instance before each test
    so APScheduler's internal thread pool doesn't carry over between tests.
    """
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        import tgai_agent.task_scheduler.scheduler as sched_mod
        # Stop running scheduler if any
        if sched_mod.scheduler._scheduler.running:
            sched_mod.scheduler._scheduler.shutdown(wait=False)
        # Replace internal scheduler with a fresh one
        sched_mod.scheduler._scheduler = AsyncIOScheduler(timezone="UTC")
    except Exception:
        pass
    yield
    try:
        import tgai_agent.task_scheduler.scheduler as sched_mod
        if sched_mod.scheduler._scheduler.running:
            sched_mod.scheduler._scheduler.shutdown(wait=False)
    except Exception:
        pass
