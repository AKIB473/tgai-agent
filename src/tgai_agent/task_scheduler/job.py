"""
task_scheduler/job.py — Job data model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Job:
    """Runtime representation of a scheduled task."""

    id: str
    user_id: int
    name: str
    trigger_type: str           # 'once' | 'interval' | 'cron'
    trigger_value: str          # ISO timestamp | seconds | cron expression
    action_type: str            # 'message' | 'agent_task' | 'plugin'
    action_payload: dict        # varies by action_type
    is_active: bool = True
    run_count: int = 0
    description: str = ""

    def __post_init__(self):
        if self.trigger_type not in ("once", "interval", "cron"):
            raise ValueError(f"Invalid trigger_type: {self.trigger_type!r}")
        if self.action_type not in ("message", "agent_task", "plugin"):
            raise ValueError(f"Invalid action_type: {self.action_type!r}")

    @classmethod
    def from_db_row(cls, row: dict) -> "Job":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            trigger_type=row["trigger_type"],
            trigger_value=row["trigger_value"],
            action_type=row["action_type"],
            action_payload=row["action_payload"],  # already parsed from JSON
            is_active=bool(row["is_active"]),
            run_count=row.get("run_count", 0),
            description=row.get("description", ""),
        )
