#!/bin/bash
# Install Playwright + Chromium for WhatsApp Web QR-scan integration.
set -e
cd "$(dirname "$0")"

echo "📦 Installing playwright (Python)..."
python3 -m pip install --user playwright

echo "🌐 Downloading Chromium..."
python3 -m playwright install chromium

echo ""
echo "✅ Done. Next steps:"
echo "   1) bash start.sh"
echo "   2) Open http://127.0.0.1:5001/whatsapp/qr"
echo "   3) Scan the QR code with your phone's WhatsApp"
