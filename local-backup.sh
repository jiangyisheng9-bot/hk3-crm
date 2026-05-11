#!/bin/bash
# HK3 CRM — 本地完整备份（含数据库）
# 用法: bash local-backup.sh
# 输出: local-backup/HK3_CRM_YYYY-MM-DD_HHMMSS.tar.gz

DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$DIR/local-backup"
mkdir -p "$BACKUP_DIR"

TODAY=$(date +%Y-%m-%d_%H%M%S)
OUTPUT="$BACKUP_DIR/HK3_CRM_$TODAY.tar.gz"

# 打包代码 + 数据库（本地保留数据）
tar czf "$OUTPUT" \
  -C "$DIR" \
  app.py \
  templates/ \
  hk3_crm.db \
  requirements.txt \
  start.sh \
  backup.sh

echo "✅ 本地备份完成: $OUTPUT"
ls -lh "$OUTPUT"
