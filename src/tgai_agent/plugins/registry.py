"""
plugins/registry.py — Plugin registry with auto-discovery.

All plugins in plugins/builtin/ are auto-registered on startup.
Third-party plugins can register via PluginRegistry.register().
"""

from __future__ import annotations

import importlib
import pkgutil
import time
from typing import Dict, Optional

from tgai_agent.plugins.base_plugin import BasePlugin, PluginError
from tgai_agent.storage.database import get_db
from tgai_agent.utils.helpers import utcnow
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)


class PluginRegistry:
    _plugins: dict[str, BasePlugin] = {}

    @classmethod
    def register(cls, plugin: BasePlugin) -> None:
        if not plugin.name:
            raise ValueError(f"Plugin {plugin.__class__} has no name")
        cls._plugins[plugin.name] = plugin
        log.debug("plugin.registered", name=plugin.name)

    @classmethod
    def get(cls, name: str) -> BasePlugin | None:
        return cls._plugins.get(name)

    @classmethod
    def list_all(cls) -> list[BasePlugin]:
        return list(cls._plugins.values())

    @classmethod
    def autodiscover(cls) -> None:
        """Import all modules in plugins/builtin/ to trigger registration."""
        import tgai_agent.plugins.builtin as builtin_pkg

        for _, module_name, _ in pkgutil.iter_modules(builtin_pkg.__path__):
            full_name = f"tgai_agent.plugins.builtin.{module_name}"
            try:
                importlib.import_module(full_name)
                log.debug("plugin.autodiscovered", module=full_name)
            except Exception as exc:
                log.warning("plugin.autodiscover_failed", module=full_name, error=str(exc))

    @classmethod
    async def run(
        cls,
        name: str,
        params: dict,
        context: dict,
    ) -> str:
        """
        Execute a plugin by name, with audit logging.

        Args:
            name:    Plugin name
            params:  Input params
            context: Runtime context dict (must include user_id)

        Returns:
            Plugin output string.
        """
        plugin = cls.get(name)
        if not plugin:
            raise PluginError(f"Unknown plugin: {name!r}")

        user_id = context.get("user_id", 0)
        start = time.monotonic()
        success = False
        result_snippet = ""

        try:
            validated = plugin.validate_params(params)
            result = await plugin.execute(validated, context)
            success = True
            result_snippet = str(result)[:200]
            return result
        except PluginError:
            raise
        except Exception as exc:
            log.error("plugin.execution_error", plugin=name, error=str(exc))
            raise PluginError(f"Plugin '{name}' encountered an error: {exc}") from exc
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            await _log_execution(
                user_id=user_id,
                plugin_name=name,
                params=params,
                result_snippet=result_snippet,
                duration_ms=duration_ms,
                success=success,
            )


async def _log_execution(
    user_id: int,
    plugin_name: str,
    params: dict,
    result_snippet: str,
    duration_ms: int,
    success: bool,
) -> None:
    import json

    now = utcnow().isoformat()
    try:
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO plugin_logs
                    (user_id, plugin_name, params_json, result_snippet, duration_ms, success, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    plugin_name,
                    json.dumps(params),
                    result_snippet,
                    duration_ms,
                    int(success),
                    now,
                ),
            )
            await db.commit()
    except Exception as exc:
        log.warning("plugin.audit_log_failed", error=str(exc))
