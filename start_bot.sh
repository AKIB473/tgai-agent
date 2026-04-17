#!/bin/bash
cd /root/.openclaw/workspace/tgai-agent
exec .venv/bin/python -m tgai_agent.main >> bot.log 2>&1
