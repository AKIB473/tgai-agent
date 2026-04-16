"""
task_scheduler/executor.py — Executes a job based on its action_type.
"""

from __future__ import annotations

from tgai_agent.task_scheduler.job import Job
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


async def execute_job(job: Job, bot, context: dict) -> None:
    """
    Dispatch job to the appropriate handler based on action_type.

    Args:
        job:     The job to execute.
        bot:     The python-telegram-bot Application instance.
        context: Extra runtime context (e.g. user chat_ids).
    """
    log.info("job.executing", job_id=job.id, name=job.name, action=job.action_type)

    try:
        if job.action_type == "message":
            await _execute_message(job, bot)
        elif job.action_type == "agent_task":
            await _execute_agent_task(job, context)
        elif job.action_type == "plugin":
            await _execute_plugin(job, context)
        else:
            log.warning("job.unknown_action", action=job.action_type)
    except Exception as exc:
        log.error("job.execution_failed", job_id=job.id, error=str(exc))


async def _execute_message(job: Job, bot) -> None:
    """Send a pre-defined message to a chat."""
    payload = job.action_payload
    chat_id = payload.get("chat_id")
    text = payload.get("text", "")
    if not chat_id or not text:
        log.warning("job.message_missing_fields", job_id=job.id)
        return
    await bot.bot.send_message(chat_id=chat_id, text=text)
    log.info("job.message_sent", job_id=job.id, chat_id=chat_id)


async def _execute_agent_task(job: Job, context: dict) -> None:
    """Hand off a task description to an agent."""
    from tgai_agent.agent_manager.manager import talk_to_agent

    payload = job.action_payload
    agent_id = payload.get("agent_id")
    task = payload.get("task", "")
    if not agent_id or not task:
        log.warning("job.agent_task_missing_fields", job_id=job.id)
        return

    result = await talk_to_agent(agent_id, job.user_id, task)
    log.info("job.agent_task_done", job_id=job.id, result_preview=result[:80])


async def _execute_plugin(job: Job, context: dict) -> None:
    """Execute a plugin with stored params."""
    from tgai_agent.plugins.registry import PluginRegistry

    payload = job.action_payload
    plugin_name = payload.get("plugin")
    params = payload.get("params", {})
    plugin_context = {**context, "user_id": job.user_id}

    result = await PluginRegistry.run(plugin_name, params, plugin_context)
    log.info("job.plugin_done", job_id=job.id, plugin=plugin_name, result_preview=result[:80])
