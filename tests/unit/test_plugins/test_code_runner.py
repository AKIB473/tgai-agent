"""Tests for the sandboxed Python code runner."""

import pytest
from tgai_agent.plugins.base_plugin import PluginError
from tgai_agent.plugins.builtin.code_runner import CodeRunnerPlugin

plugin = CodeRunnerPlugin()
ctx = {"user_id": 1}


@pytest.mark.asyncio
async def test_simple_print():
    result = await plugin.execute({"code": "print(1 + 1)"}, ctx)
    assert "2" in result


@pytest.mark.asyncio
async def test_math_expression():
    result = await plugin.execute({"code": "print(2 ** 10)"}, ctx)
    assert "1024" in result


@pytest.mark.asyncio
async def test_no_code_raises():
    with pytest.raises(PluginError, match="No code"):
        await plugin.execute({"code": ""}, ctx)


@pytest.mark.asyncio
async def test_syntax_error_raises():
    with pytest.raises(PluginError, match="Syntax error"):
        await plugin.execute({"code": "def bad(:"}, ctx)


@pytest.mark.asyncio
async def test_import_blocked():
    """OS module must not be accessible in sandbox."""
    with pytest.raises(PluginError):
        await plugin.execute({"code": "import os; print(os.getcwd())"}, ctx)


@pytest.mark.asyncio
async def test_runtime_error_raises():
    with pytest.raises(PluginError, match="Runtime error"):
        await plugin.execute({"code": "1 / 0"}, ctx)
