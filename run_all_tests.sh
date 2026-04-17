#!/bin/bash
set -e
cd /root/.openclaw/workspace/tgai-agent
.venv/bin/python -m pytest tests/ -v --tb=short --no-header -p no:cacheprovider 2>&1
