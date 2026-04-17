#!/bin/bash
# Quick verification of the three fix areas
cd /root/.openclaw/workspace/tgai-agent

echo "=== 1. Testing PrintCollector fix ==="
.venv/bin/python -c "
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import safe_builtins
from RestrictedPython.PrintCollector import PrintCollector

code = 'print(\"hello world\")'
byte_code = compile_restricted(code, '<sandbox>', 'exec')
globs = {**safe_globals, '__builtins__': safe_builtins, '__name__': '__sandbox__', '_print_': PrintCollector, '_getattr_': getattr}
exec(byte_code, globs)
printer = globs.get('_print')
output = printer() if callable(printer) else ''
print('Output:', repr(output))
assert 'hello world' in output, f'FAIL: expected hello world in {output!r}'
print('PASS: PrintCollector works')
"

echo ""
echo "=== 2. Testing message_handler talk_to_agent import ==="
.venv/bin/python -c "
import sys
sys.path.insert(0, 'src')
import tgai_agent.bot_interface.handlers.message_handler as mh
assert hasattr(mh, 'talk_to_agent'), 'FAIL: talk_to_agent not on module'
print('PASS: talk_to_agent found on message_handler module')
"

echo ""
echo "=== 3. Testing asyncio_default_fixture_loop_scope ==="
.venv/bin/python -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    config = tomllib.load(f)
scope = config['tool']['pytest']['ini_options'].get('asyncio_default_fixture_loop_scope')
print(f'asyncio_default_fixture_loop_scope = {scope!r}')
assert scope == 'function', f'FAIL: expected function, got {scope}'
print('PASS: loop scope is function')
"

echo ""
echo "=== 4. Running targeted pytest tests ==="
.venv/bin/python -m pytest \
  tests/unit/test_plugins/test_code_runner.py::test_basic_print \
  tests/unit/test_plugins/test_code_runner.py::test_arithmetic \
  tests/unit/test_plugins/test_code_runner.py::test_list_comprehension \
  "tests/unit/test_bot/test_message_handler.py::TestAgentTalkMode::test_agent_talk_mode_routes_to_agent" \
  "tests/unit/test_bot/test_message_handler.py::TestAgentTalkMode::test_done_command_exits_agent_talk_mode" \
  tests/unit/test_storage/test_repositories.py::test_upsert_and_get_user \
  tests/unit/test_ai_core/test_memory.py::test_short_term_add_and_get \
  tests/unit/test_security/test_permissions.py::test_unknown_user_is_regular_user \
  -v --tb=short --no-header --no-cov 2>&1

echo ""
echo "=== 5. Full test suite ==="
.venv/bin/python -m pytest tests/ --tb=short --no-header 2>&1 | tail -60
