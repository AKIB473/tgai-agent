"""Tests for CodeRunnerPlugin sandboxed execution."""

import pytest

from tgai_agent.plugins.base_plugin import PluginError
from tgai_agent.plugins.builtin.code_runner import CodeRunnerPlugin


@pytest.fixture
def plugin():
    return CodeRunnerPlugin()


@pytest.fixture
def context():
    return {"user_id": 1, "chat_id": 100}


@pytest.mark.asyncio
async def test_basic_print(plugin, context):
    result = await plugin.execute({"code": "print('hello world')"}, context)
    assert "hello world" in result


@pytest.mark.asyncio
async def test_arithmetic(plugin, context):
    result = await plugin.execute({"code": "print(2 + 2)"}, context)
    assert "4" in result


@pytest.mark.asyncio
async def test_multiline_code(plugin, context):
    code = "x = 10\ny = 20\nprint(x + y)"
    result = await plugin.execute({"code": code}, context)
    assert "30" in result


@pytest.mark.asyncio
async def test_no_output(plugin, context):
    result = await plugin.execute({"code": "x = 1 + 1"}, context)
    assert "no output" in result.lower()


@pytest.mark.asyncio
async def test_blocks_os_import(plugin, context):
    with pytest.raises(PluginError):
        await plugin.execute({"code": "import os; print(os.getcwd())"}, context)


@pytest.mark.asyncio
async def test_blocks_sys_import(plugin, context):
    with pytest.raises(PluginError):
        await plugin.execute({"code": "import sys; print(sys.version)"}, context)


@pytest.mark.asyncio
async def test_blocks_open_builtin(plugin, context):
    with pytest.raises(PluginError):
        await plugin.execute({"code": "open('/etc/passwd').read()"}, context)


@pytest.mark.asyncio
async def test_syntax_error_raises(plugin, context):
    with pytest.raises(PluginError, match="[Ss]yntax"):
        await plugin.execute({"code": "def foo(: pass"}, context)


@pytest.mark.asyncio
async def test_runtime_error_raises(plugin, context):
    with pytest.raises(PluginError, match="[Rr]untime"):
        await plugin.execute({"code": "1/0"}, context)


@pytest.mark.asyncio
async def test_name_error_raises(plugin, context):
    with pytest.raises(PluginError, match="[Rr]untime"):
        await plugin.execute({"code": "print(undefined_variable)"}, context)


@pytest.mark.asyncio
async def test_empty_code_raises(plugin, context):
    with pytest.raises(PluginError):
        await plugin.execute({"code": ""}, context)


@pytest.mark.asyncio
async def test_output_truncated(plugin, context):
    code = "print('x' * 5000)"
    result = await plugin.execute({"code": code}, context)
    assert "truncated" in result or len(result) < 3000


@pytest.mark.asyncio
async def test_list_comprehension(plugin, context):
    result = await plugin.execute({"code": "print([x**2 for x in range(5)])"}, context)
    assert "0" in result
    assert "16" in result


@pytest.mark.asyncio
async def test_string_operations(plugin, context):
    result = await plugin.execute({"code": "s = 'hello'; print(s.upper())"}, context)
    assert "HELLO" in result


@pytest.mark.asyncio
async def test_plugin_properties(plugin):
    assert plugin.name == "run_python"
    assert plugin.requires_confirmation is True
    assert plugin.is_safe is False
    assert "sandbox" in plugin.description.lower() or "secure" in plugin.description.lower()
