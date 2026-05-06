#!/usr/bin/env python3
"""Import repurchase reminder dates from Google Sheet into CRM FollowUps."""
import os, sys
from datetime import datetime, date

sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace/hk3-crm"))
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app import app, db, Customer, FollowUp

CRED_FILE = os.path.expanduser("~/.openclaw/workspace/.gsheet-credentials.json")
SHEET_ID = "1G_Jnm-hoHnnyj8LEimNR3bgbUJGsh4yiNlJiETTASnM"

# Read sheet
creds = service_account.Credentials.from_service_account_file(
    CRED_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheets = build("sheets", "v4", credentials=creds)
result = sheets.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range="客户记录!B:Z"
).execute()
rows = result.get("values", [])
data = rows[1:] if len(rows) > 1 else []

print(f"📊 Found {len(data)} records in sheet")

def gen_followup_id():
    today = date.today().strftime('%Y%m%d')
    count = FollowUp.query.filter(FollowUp.followup_id.like(f'FLW-{today}-%')).count() + 1
    return f'FLW-{today}-{count:03d}'

with app.app_context():
    created = 0
    skipped = 0
    errors = 0
    
    for i, row in enumerate(data):
        try:
            name = row[0].strip() if row and len(row) > 0 and row[0] else ''
            reminder_str = row[20].strip() if row and len(row) > 20 and row[20] else ''
            product = row[9].strip() if row and len(row) > 9 and row[9] else ''
            last_order = row[23].strip() if row and len(row) > 23 and row[23] else ''
            
            if not name or not reminder_str:
                continue
            
            # Parse reminder date
            try:
                remind_date = datetime.strptime(reminder_str, '%Y-%m-%d')
            except:
                print(f"  ⚠️  [{i+1}] {name}: 日期格式不对 '{reminder_str}'")
                errors += 1
                continue
            
            # Find customer - try by name first
            customer = Customer.query.filter(Customer.name == name).first()
            
            # Try partial match
            if not customer:
                # Try removing parenthetical
                clean_name = name.split(' (')[0].split('（')[0].strip()
                customer = Customer.query.filter(Customer.name.contains(clean_name)).first()
            
            if not customer:
                print(f"  ❌ [{i+1}] {name}: 在 CRM 中找不到匹配客户")
                errors += 1
                continue
            
            # Check if followup already exists for this customer + reminder
            existing = FollowUp.query.filter(
                FollowUp.customer_id == customer.id,
                FollowUp.type == '复购提醒',
                FollowUp.scheduled_at >= remind_date,
            ).first()
            
            if existing:
                print(f"  ⏭️  [{i+1}] {name} → 已有复购提醒 ({existing.scheduled_at.date()})")
                skipped += 1
                continue
            
            # Create followup
            f = FollowUp(
                followup_id=gen_followup_id(),
                customer_id=customer.id,
                type='复购提醒',
                trigger_reason=f'产品预计用完，建议复购（{product}）' if product else '建议复购',
                scheduled_at=remind_date,
                status='待执行',
                content=f'📅 回购提醒日期：{reminder_str}\n📦 上次购买产品：{product or "未知"}\n🕐 上次购买：{last_order or "未知"}\n💡 联系客户询问是否需要复购。',
                generated_by='GoogleSheet-Migration'
            )
            db.session.add(f)
            created += 1
            print(f"  ✅ [{i+1}] {name} → 复购提醒 {remind_date.date()}")
            
        except Exception as e:
            print(f"  ❌ [{i+1}] Error: {e}")
            errors += 1
    
    db.session.commit()
    print(f"\n{'='*50}")
    print(f"📊 导入完成！")
    print(f"  ✅ 新增复购提醒: {created}")
    print(f"  ⏭️  已跳过（已有）: {skipped}")
    print(f"  ❌ 错误: {errors}")
    print(f"  📋 跟进总任务: {FollowUp.query.count()}")
