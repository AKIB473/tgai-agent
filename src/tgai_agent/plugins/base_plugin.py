"""
plugins/base_plugin.py — Abstract base class for all plugins (tools).

Every plugin is a self-contained unit with:
  - A unique `name`
  - A human-readable `description`
  - An `execute(params, context)` coroutine
  - Optional `parameter_schema` for validation

Plugins receive a `context` dict with:
    - user_id: int
    - chat_id: int
    - bot: telegram Application instance
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BasePlugin(ABC):
    name: str = ""
    description: str = ""
    parameter_schema: dict = {}  # JSON Schema for params (optional)
    requires_confirmation: bool = False  # Ask user before running?
    is_safe: bool = True  # If False, extra security checks apply

    @abstractmethod
    async def execute(self, params: dict, context: dict) -> str:
        """
        Run the plugin.

        Args:
            params:  Validated input parameters.
            context: Runtime context (user_id, chat_id, bot, ...).

        Returns:
            A string result that will be shown to the user / fed to the AI.

        Raises:
            PluginError: On expected failures (shown to user).
            Exception:   Unexpected errors (caught by registry, logged).
        """

    def validate_params(self, params: dict) -> dict:
        """
        Basic param validation. Override for custom logic.
        Returns validated params dict.
        """
        return params

    def __repr__(self) -> str:
        return f"Plugin(name={self.name!r})"


class PluginError(Exception):
    """User-facing plugin error. Message will be shown in chat."""
