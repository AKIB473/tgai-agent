#!/bin/bash
cd /root/.openclaw/workspace/tgai-agent
.venv/bin/python -m pytest tests/unit/test_storage/test_repositories.py::test_upsert_and_get_user -v --tb=long --no-header 2>&1
echo "---"
.venv/bin/python -m pytest tests/unit/test_ai_core/test_memory.py::test_short_term_add_and_get -v --tb=long --no-header 2>&1
echo "---"
.venv/bin/python -m pytest tests/unit/test_plugins/test_code_runner.py::test_basic_print -v --tb=long --no-header 2>&1
echo "---"
.venv/bin/python -m pytest "tests/unit/test_bot/test_message_handler.py::TestAgentTalkMode::test_agent_talk_mode_routes_to_agent" -v --tb=long --no-header 2>&1
