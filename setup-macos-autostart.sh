#!/bin/bash
# HK3 CRM — macOS 开机自启安装脚本
# 用法: bash setup-macos-autostart.sh
set -e

CRM_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_SRC="$CRM_DIR/com.hk3.crm.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.hk3.crm.plist"

echo "🔧 安装 HK3 CRM 开机自启..."

# Generate plist with correct paths
cat > "$PLIST_DEST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hk3.crm</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>${CRM_DIR}/app.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${CRM_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/hk3-crm.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/hk3-crm.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

# Load it
launchctl load "$PLIST_DEST" 2>/dev/null || launchctl load "$PLIST_DEST"
sleep 2

echo "✅ 开机自启已安装！"
echo "📊 http://127.0.0.1:5001"
echo ""
echo "📋 管理命令："
echo "   卸载: launchctl unload ~/Library/LaunchAgents/com.hk3.crm.plist"
echo "   状态: launchctl list com.hk3.crm"
echo "   日志: tail -f /tmp/hk3-crm.log"
