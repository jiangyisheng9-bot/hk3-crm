#!/bin/bash
# HK3 CRM — 安全重启脚本
# 用法: bash restart.sh
set -e
cd "$(dirname "$0")"
echo "🔄 正在重启 HK3 CRM..."
sleep 1
# Kill old process
pkill -f "python3.*app.py" 2>/dev/null || true
sleep 2
# Start new
nohup python3 app.py > /tmp/hk3-crm.log 2>&1 &
echo "✅ 已重启 (PID $!)"
echo "📊 http://127.0.0.1:5001"
