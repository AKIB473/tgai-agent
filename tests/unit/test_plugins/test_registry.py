"""Tests for the plugin registry."""

import pytest

from tgai_agent.plugins.base_plugin import BasePlugin, PluginError
from tgai_agent.plugins.registry import PluginRegistry


class _EchoPlugin(BasePlugin):
    name = "test_echo"
    description = "Echoes the input"

    async def execute(self, params: dict, context: dict) -> str:
        return f"echo: {params.get('text', '')}"


class _FailPlugin(BasePlugin):
    name = "test_fail"
    description = "Always fails"

    async def execute(self, params: dict, context: dict) -> str:
        raise PluginError("Intentional failure")


def test_register_and_get():
    PluginRegistry.register(_EchoPlugin())
    plugin = PluginRegistry.get("test_echo")
    assert plugin is not None
    assert plugin.name == "test_echo"


def test_get_unknown_returns_none():
    assert PluginRegistry.get("does_not_exist") is None


@pytest.mark.asyncio
async def test_run_echo_plugin():
    PluginRegistry.register(_EchoPlugin())
    result = await PluginRegistry.run("test_echo", {"text": "hello"}, {"user_id": 1})
    assert result == "echo: hello"


@pytest.mark.asyncio
async def test_run_unknown_plugin_raises():
    with pytest.raises(PluginError, match="Unknown plugin"):
        await PluginRegistry.run("nonexistent", {}, {"user_id": 1})


@pytest.mark.asyncio
async def test_run_failing_plugin_raises_plugin_error():
    PluginRegistry.register(_FailPlugin())
    with pytest.raises(PluginError, match="Intentional failure"):
        await PluginRegistry.run("test_fail", {}, {"user_id": 1})
