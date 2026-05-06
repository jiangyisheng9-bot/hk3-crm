#!/usr/bin/env python3
"""Import Google Sheet data into HK3 CRM SQLite database."""
import os, sys, json, uuid, re
from datetime import datetime, date
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Setup: add hk3-crm to path
sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace/hk3-crm"))
from app import app, db, Customer, Order

CRED_FILE = os.path.expanduser("~/.openclaw/workspace/.gsheet-credentials.json")
SHEET_ID = "1G_Jnm-hoHnnyj8LEimNR3bgbUJGsh4yiNlJiETTASnM"

# Read sheet
creds = service_account.Credentials.from_service_account_file(
    CRED_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheets = build("sheets", "v4", credentials=creds)
result = sheets.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range="客户记录!A:Z"
).execute()
rows = result.get("values", [])

if not rows:
    print("❌ No data found")
    sys.exit(1)

header = rows[0]
data = rows[1:]  # skip header
print(f"📊 Found {len(data)} customer records to import")

# Status mapping
STATUS_MAP = {
    '已送达': '已签收', '已发货': '已发货', '待发货': '待发货',
    '已完成': '已签收', '已取消': '已取消', '退款': '退款',
    '待付款': '待付款', '已付款': '已付款'
}

def clean_phone(p):
    """Clean phone to +60 format"""
    if not p:
        return None
    p = p.strip().replace(' ', '').replace('-', '').replace('+', '')
    if p.startswith('60') and len(p) >= 10:
        return f'+{p}'
    if p.startswith('0'):
        return f'+60{p[1:]}'
    return p

def parse_date(d):
    """Parse date string"""
    if not d:
        return None
    try:
        return datetime.strptime(d.strip(), '%Y-%m-%d')
    except:
        return None

def gen_customer_id():
    """Generate unique customer ID"""
    today = date.today().strftime('%Y%m%d')
    count = Customer.query.filter(Customer.customer_id.like(f'HK3-{today}-%')).count() + 1
    return f'HK3-{today}-{count:03d}'

def gen_order_id():
    today = date.today().strftime('%Y%m%d')
    count = Order.query.filter(Order.order_id.like(f'ORD-{today}-%')).count() + 1
    return f'ORD-{today}-{count:03d}'

# Run import within app context
with app.app_context():
    imported = 0
    skipped = 0
    orders_created = 0
    
    for row in data:
        try:
            # Ensure row has enough columns
            while len(row) < 26:
                row.append('')
            
            name = row[1].strip() if row[1] else ''
            phone_wa = clean_phone(row[8] if len(row) > 8 else '')
            phone_other = clean_phone(row[7] if len(row) > 7 else '')
            state = row[6].strip() if len(row) > 6 and row[6] else ''
            city = row[4].strip() if len(row) > 4 and row[4] else ''
            addr1 = row[2].strip() if len(row) > 2 and row[2] else ''
            addr2 = row[3].strip() if len(row) > 3 and row[3] else ''
            zipcode = row[5].strip() if len(row) > 5 and row[5] else ''
            
            shipping_addr = ', '.join(filter(None, [addr1, addr2, city, zipcode, state]))
            
            product = row[11].strip() if len(row) > 11 and row[11] else ''
            quantity = row[12].strip() if len(row) > 12 and row[12] else '1'
            payment = row[13].strip() if len(row) > 13 and row[13] else ''
            order_date_str = row[14].strip() if len(row) > 14 and row[14] else ''
            order_status_raw = row[15].strip() if len(row) > 15 and row[15] else '待发货'
            order_status = STATUS_MAP.get(order_status_raw, '待发货')
            courier = row[16].strip() if len(row) > 16 and row[16] else ''
            tracking = row[17].strip() if len(row) > 17 and row[17] else ''
            source_raw = row[19].strip() if len(row) > 19 and row[19] else ''
            tags_raw = row[20].strip() if len(row) > 20 and row[20] else ''
            notes_raw = row[22].strip() if len(row) > 22 and row[22] else ''
            total_order_count = row[23].strip() if len(row) > 23 and row[23] else '1'
            last_order_date_str = row[24].strip() if len(row) > 24 and row[24] else ''
            messenger_name = row[10].strip() if len(row) > 10 and row[10] else ''
            
            # Determine acquisition source
            source = source_raw
            fb_page = row[9].strip() if len(row) > 9 and row[9] else ''
            if not source:
                if '瘦身咖啡' in fb_page or 'Facebook' in fb_page:
                    source = 'FB广告'
                elif messenger_name:
                    source = 'FB Messenger'
                else:
                    source = '未知'
            
            # Parse dates
            order_date = parse_date(order_date_str)
            last_order_date = parse_date(last_order_date_str)
            
            # Determine funnel stage & tags
            tags = tags_raw
            total_orders_int = 1
            try:
                total_orders_int = int(total_order_count)
            except:
                pass
            
            if total_orders_int >= 2:
                funnel = '复购'
            elif order_status in ['已签收', '已发货']:
                funnel = '成交'
            elif order_date:
                funnel = '成交'
            else:
                funnel = '询盘'
            
            # Health concerns extraction from notes
            health = ''
            notes = notes_raw
            if notes:
                health_keywords = {
                    '三高': '三高', '血糖': '糖尿病/血糖高', '糖尿病': '糖尿病/血糖高',
                    '肾脏': '肾脏问题', '肾': '肾脏问题', '痛风': '痛风',
                    '高血压': '高血压', '高血糖': '糖尿病/血糖高',
                    '尿酸': '尿酸高/痛风', '瘦身': '减肥需求', '减肥': '减肥需求'
                }
                health_notes = []
                for kw, label in health_keywords.items():
                    if kw in notes:
                        health_notes.append(label)
                if health_notes:
                    health = ','.join(set(health_notes))
            
            # Courier preference
            pref_courier = ''
            if notes and ('poslaju' in notes.lower() or 'pos laju' in notes.lower()):
                if '不' in notes and ('pos' in notes.lower()):
                    pref_courier = '其他（不要PosLaju）'
                else:
                    pref_courier = 'PosLaju'
            if courier and not pref_courier:
                pref_courier = courier
            
            # Check for duplicate by phone WA
            existing = None
            if phone_wa:
                existing = Customer.query.filter_by(phone_whatsapp=phone_wa).first()
            if not existing and name:
                existing = Customer.query.filter_by(name=name).first()
            
            if existing:
                print(f"  ⏭️ [{row[0]}] {name} — 已有，更新")
                # Update existing record
                if phone_wa and not existing.phone_whatsapp:
                    existing.phone_whatsapp = phone_wa
                if not existing.preferred_courier and pref_courier:
                    existing.preferred_courier = pref_courier
                if health and not existing.health_concerns:
                    existing.health_concerns = health
                if notes and existing.notes:
                    existing.notes += '\n' + notes
                elif notes:
                    existing.notes = notes
                if total_orders_int > (existing.total_orders or 0):
                    existing.total_orders = total_orders_int
                if last_order_date and (not existing.last_order_date or last_order_date.date() > existing.last_order_date):
                    existing.last_order_date = last_order_date.date()
                db.session.flush()
                cid = existing.id
                skipped += 1
            else:
                c = Customer(
                    customer_id=gen_customer_id(),
                    name=name,
                    phone_whatsapp=phone_wa,
                    phone_other=phone_other,
                    location_state=state,
                    location_city=city,
                    shipping_address=shipping_addr,
                    preferred_courier=pref_courier,
                    preferred_payment=payment or None,
                    funnel_stage=funnel,
                    rfm_segment='B（新客）' if total_orders_int < 2 else 'A（普通老客）',
                    acquisition_source=source,
                    total_orders=total_orders_int,
                    last_order_date=last_order_date.date() if last_order_date else None,
                    health_concerns=health or None,
                    tags=tags or None,
                    notes=notes or None,
                    fb_messenger_id=messenger_name or None,
                    created_by='Import-Sheet',
                    ltv=0,
                    intent_score=60,
                    engagement_score=50
                )
                db.session.add(c)
                db.session.flush()
                cid = c.id
                imported += 1
                print(f"  ✅ [{row[0]}] {name} → 新增 {c.customer_id}")
            
            # Create order from row data
            if product and order_date:
                # Check if order already exists for this customer+product+date
                existing_orders = Order.query.filter_by(
                    customer_id=cid
                ).filter(Order.order_date >= order_date).count()
                
                if existing_orders == 0:
                    # Estimate amount from product
                    prod = product
                    qty = 1
                    try:
                        qty = int(re.findall(r'\d+', quantity)[0]) if quantity else 1
                    except:
                        pass
                    
                    o = Order(
                        order_id=gen_order_id(),
                        customer_id=cid,
                        order_date=order_date,
                        order_status=order_status,
                        products=prod,
                        courier=courier or None,
                        tracking_number=tracking or None,
                        payment_method=payment or None,
                        shipping_address=shipping_addr or None,
                        notes=notes or None,
                        source=source or 'WhatsApp'
                    )
                    db.session.add(o)
                    orders_created += 1
            
        except Exception as e:
            print(f"  ❌ Error on row {row[0] if row else '?'}: {e}")
            continue
    
    db.session.commit()
    print(f"\n{'='*50}")
    print(f"📊 导入完成！")
    print(f"  ✅ 新增客户: {imported}")
    print(f"  ⏭️  更新客户: {skipped}")
    print(f"  📦 新增订单: {orders_created}")
    print(f"  👥 总客户数: {Customer.query.count()}")
    print(f"  💰 总销售额: RM {db.session.query(db.func.sum(Order.total_amount)).scalar() or 0:.2f}")
