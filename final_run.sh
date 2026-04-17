#!/bin/bash
set -o pipefail
cd /root/.openclaw/workspace/tgai-agent

echo "================================================================"
echo " STEP 1: Full pytest suite"
echo "================================================================"
.venv/bin/python -m pytest tests/ -v --tb=short --no-header 2>&1
PYTEST_EXIT=$?

echo ""
echo "================================================================"
echo " STEP 2: Bot token + DB + send message"
echo "================================================================"
.venv/bin/python bot_check.py 2>&1

echo ""
echo "================================================================"
echo " SUMMARY"
echo "================================================================"
if [ $PYTEST_EXIT -eq 0 ]; then
  echo "pytest: ALL PASSED ✅"
else
  echo "pytest: some failures (see above) ❌"
fi
