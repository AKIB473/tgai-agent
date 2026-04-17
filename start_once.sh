#!/bin/bash
# start_once.sh — Kill any existing bot instances then start exactly one

PIDFILE="/tmp/tgai_bot.pid"
LOGFILE="/tmp/tgai_bot.log"
BOTDIR="/root/.openclaw/workspace/tgai-agent"

# Kill existing instances
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    kill -9 "$OLD_PID" 2>/dev/null
    rm -f "$PIDFILE"
fi

# Kill any stray processes
pkill -9 -f "run_bot\|tgai_agent.main" 2>/dev/null
sleep 3

# Verify all dead
COUNT=$(ps aux | grep -E "run_bot|tgai_agent.main" | grep -v grep | wc -l)
if [ "$COUNT" -gt "0" ]; then
    ps aux | grep -E "run_bot|tgai_agent.main" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
    sleep 2
fi

echo "$(date): Starting bot..." > "$LOGFILE"

# Start single instance
cd "$BOTDIR"
nohup .venv/bin/python run_bot.py >> "$LOGFILE" 2>&1 &
BOT_PID=$!
echo $BOT_PID > "$PIDFILE"

echo "Bot started with PID $BOT_PID"
echo "Log: $LOGFILE"
sleep 8
echo "=== Bot Log ==="
cat "$LOGFILE"
echo "==="
ps -p $BOT_PID 2>/dev/null && echo "✅ Bot is RUNNING (PID $BOT_PID)" || echo "❌ Bot crashed"
