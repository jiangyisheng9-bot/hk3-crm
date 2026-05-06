#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$DIR/.pid"

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    kill "$OLD_PID" 2>/dev/null
    sleep 1
fi

cd "$DIR"
nohup python3 app.py > /tmp/hk3-crm.log 2>&1 &
echo $! > "$PID_FILE"
sleep 2
echo "✅ HK3 CRM started on http://127.0.0.1:5001"
echo "Log: /tmp/hk3-crm.log"
