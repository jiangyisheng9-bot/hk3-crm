#!/bin/bash
# HK3 CRM — Database Backup Script
# Saves to: ~/Desktop/HK3_CRM_Backups/

BACKUP_DIR="$HOME/Desktop/HK3_CRM_Backups"
DB_PATH="$HOME/.openclaw/workspace/hk3-crm/hk3_crm.db"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup with date in filename
cp "$DB_PATH" "$BACKUP_DIR/hk3_crm_${TIMESTAMP}.db"

# Keep a "latest" copy for easy restore
cp "$DB_PATH" "$BACKUP_DIR/hk3_crm_latest.db"

# Also backup the code (exclude db and venv)
cd "$HOME/.openclaw/workspace/hk3-crm"
git archive --format=zip -o "$BACKUP_DIR/hk3_crm_code_${TIMESTAMP}.zip" HEAD

# Clean up old backups (keep only last 30 days)
find "$BACKUP_DIR" -name "hk3_crm_*.db" -mtime +30 -delete 2>/dev/null
find "$BACKUP_DIR" -name "hk3_crm_code_*.zip" -mtime +30 -delete 2>/dev/null

# Count
DB_COUNT=$(ls "$BACKUP_DIR"/*.db 2>/dev/null | wc -l | tr -d ' ')
SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)

echo "✅ HK3 CRM 备份完成"
echo "   📁 $BACKUP_DIR"
echo "   💾 数据库: hk3_crm_${TIMESTAMP}.db"
echo "   📦 代码:   hk3_crm_code_${TIMESTAMP}.zip"
echo "   📊 共 $DB_COUNT 个备份文件（${SIZE}）"
