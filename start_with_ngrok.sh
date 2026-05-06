#!/bin/bash
# HK3 CRM + ngrok tunnel — for WhatsApp Cloud API webhook
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# 1. Make sure CRM is running
bash "$DIR/start.sh"

# 2. Check ngrok
if ! command -v ngrok >/dev/null 2>&1; then
    echo "❌ ngrok 未安装"
    echo "   安装方法：brew install ngrok/ngrok/ngrok"
    echo "   注册并 ngrok config add-authtoken <YOUR_TOKEN>"
    exit 1
fi

# 3. Kill existing ngrok if any
pkill -f "ngrok http 5001" 2>/dev/null || true
sleep 1

# 4. Start ngrok in background
echo "🌐 启动 ngrok 隧道 → http://localhost:5001 ..."
nohup ngrok http 5001 --log=stdout > /tmp/hk3-ngrok.log 2>&1 &
NGROK_PID=$!
echo "$NGROK_PID" > "$DIR/.ngrok.pid"

# 5. Wait for ngrok API to be ready and fetch public URL
echo "⏳ 等待 ngrok 启动..."
PUBLIC_URL=""
for i in {1..15}; do
    sleep 1
    PUBLIC_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | \
                 python3 -c "import sys,json; d=json.load(sys.stdin); t=d.get('tunnels',[]); print(t[0]['public_url'] if t else '')" 2>/dev/null || echo "")
    if [ -n "$PUBLIC_URL" ]; then break; fi
done

if [ -z "$PUBLIC_URL" ]; then
    echo "❌ 无法获取 ngrok 公网 URL，请检查 /tmp/hk3-ngrok.log"
    exit 1
fi

echo ""
echo "✅ HK3 CRM + ngrok 已启动！"
echo "──────────────────────────────────────────────"
echo "📊 本地访问:    http://127.0.0.1:5001"
echo "🌐 公网访问:    $PUBLIC_URL"
echo "🔗 Webhook URL: $PUBLIC_URL/whatsapp/webhook"
echo "──────────────────────────────────────────────"
echo "👉 把 Webhook URL 填到 Meta for Developers → WhatsApp → Configuration"
echo ""
echo "📝 日志:"
echo "   CRM:   tail -f /tmp/hk3-crm.log"
echo "   ngrok: tail -f /tmp/hk3-ngrok.log"
echo ""
echo "🛑 关闭：bash stop_ngrok.sh  或  kill \$(cat .pid) \$(cat .ngrok.pid)"
