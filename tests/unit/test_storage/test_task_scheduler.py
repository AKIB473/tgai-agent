"""Tests for task scheduler job model."""

import pytest
from tgai_agent.task_scheduler.job import Job


def _make_job(**kwargs) -> Job:
    defaults = dict(
        id="abc-123",
        user_id=1,
        name="test",
        trigger_type="interval",
        trigger_value="60",
        action_type="message",
        action_payload={"chat_id": 123, "text": "hello"},
    )
    defaults.update(kwargs)
    return Job(**defaults)


def test_job_creation():
    job = _make_job()
    assert job.id == "abc-123"
    assert job.trigger_type == "interval"


def test_job_invalid_trigger_type():
    with pytest.raises(ValueError, match="trigger_type"):
        _make_job(trigger_type="invalid")


def test_job_invalid_action_type():
    with pytest.raises(ValueError, match="action_type"):
        _make_job(action_type="unknown")


def test_job_from_db_row():
    row = {
        "id": "xyz",
        "user_id": 42,
        "name": "my_task",
        "trigger_type": "cron",
        "trigger_value": "0 9 * * 1",
        "action_type": "plugin",
        "action_payload": {"plugin": "web_search", "params": {"query": "news"}},
        "is_active": 1,
        "run_count": 5,
        "description": "weekly news",
    }
    job = Job.from_db_row(row)
    assert job.name == "my_task"
    assert job.run_count == 5
    assert job.is_active is True
