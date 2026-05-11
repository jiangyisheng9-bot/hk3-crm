#!/usr/bin/env python3
"""
HK3 CRM — 演示数据生成器
供代理下载后运行，生成假客户数据用于体验系统功能。
用法: python3 seed_demo.py
数据标记: 所有客户备注含 [DEMO]，方便清理
"""

import os, sys, random, json
from datetime import datetime, timedelta, date
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, Customer, Order, Interaction, FollowUp, Product, generate_id, FUNNEL_STAGES

# ─── 虚构的马来西亚客户数据 ───

NAMES = ["陈伟强", "林美玲"]

HEALTH_CONCERNS = [
    "糖尿病II型,肾虚", "高血糖,夜尿频繁", "尿酸高,痛风",
    "肾衰竭早期,漏蛋白", "高血压,腰酸", "糖尿病,尿泡",
    "肾病,脚肿", "高血糖,睡眠差", "痛风,尿酸", "糖尿病I型",
    "肾结石,腰痛", "高血压,高血糖", "尿频,尿不完",
    "肾功能低下,疲劳", "糖尿病II型,肥胖", "尿酸高",
    "夜尿3-4次,泡沫尿", "肾病综合症", "血糖不稳,头晕", "痛风发作",
]

PHONE_PREFIX = ['012', '016', '017', '019', '011']

def fake_phone():
    prefix = random.choice(PHONE_PREFIX)
    return f'{prefix}-{random.randint(1000000, 9999999)}'

STATES = ['Johor', 'KL', 'Selangor', 'Penang', 'Perak', 'Pahang', 'Kedah', 'Melaka']
CITIES = {
    'Johor': ['Johor Bahru', 'Batu Pahat', 'Muar', 'Pontian', 'Kluang'],
    'KL': ['Cheras', 'Kepong', 'Setapak', 'Damansara', 'Wangsa Maju'],
    'Selangor': ['Puchong', 'Subang', 'Shah Alam', 'Petaling Jaya', 'Klang'],
    'Penang': ['George Town', 'Bukit Mertajam', 'Butterworth'],
    'Perak': ['Ipoh', 'Taiping', 'Teluk Intan'],
    'Pahang': ['Kuantan', 'Bentong', 'Temerloh'],
}

SOURCES = ['FB广告', '转介绍', 'WhatsApp', 'TikTok', 'Lazada', '线下活动']

# 生成代理专用 Markdown 说明
HELP_TEXT = """
# HK3 CRM — 代理使用指南（演示模式）

## 已加载演示数据
- 2 个假客户（体验系统功能）
- 订单记录
- 跟进任务
- 互动记录

## 数据特征
- 所有客户备注含 **[DEMO]** 标记
- 手机号码为虚构号码
- 健康问题为随机生成
- **不含真实客户信息**

## 清理演示数据
当你要开始录入真实客户时，运行：
```bash
python3 seed_demo.py --clean
```

## 更新代码后数据会消失吗？
**不会。** 数据库文件（hk3_crm.db）在 .gitignore 中，git pull 不会动它。
即使以后有 schema 变更，系统会自动处理。

## 建议工作流
1. 先体验演示数据 → 熟悉系统
2. 运行 --clean 清空演示数据
3. 开始录入真实客户
"""

def seed_demo():
    with app.app_context():
        # Check if demo data already exists
        existing = Customer.query.filter(Customer.notes.like('%[DEMO]%')).first()
        if existing:
            print("⚠️ 演示数据已存在。运行 python3 seed_demo.py --clean 清空后重新生成。")
            return

        # Ensure products exist
        products = {
            '竹盐咖啡（无糖版）': 45.0,
            'GlucoDNA 基因护肾': 188.0,
            '去糖灵': 128.0,
            '3x竹盐': 28.0,
            '9x竹盐（药用级）': 68.0,
            'Cardio Xupport': 128.0,
            'RespVit 呼吸配方': 98.0,
            '紫竹盐': 48.0,
        }

        # Create customers
        customers = []
        for i, name in enumerate(NAMES):
            state = random.choice(STATES)
            city = random.choice(CITIES.get(state, CITIES['KL']))
            stage = random.choices(
                FUNNEL_STAGES[:6],
                weights=[10, 15, 20, 30, 15, 10]
            )[0]

            c = Customer(
                customer_id=generate_id('DEMO'),
                name=name,
                phone_whatsapp=fake_phone(),
                phone_other=fake_phone(),
                location_state=state,
                location_city=city,
                funnel_stage=stage,
                health_concerns=random.choice(HEALTH_CONCERNS),
                acquisition_source=random.choice(SOURCES),
                notes=f'[DEMO] 演示客户 #{i+1}',
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60)),
            )
            db.session.add(c)
            db.session.flush()
            customers.append(c)

        db.session.commit()
        print(f'✅ 已创建 {len(customers)} 个演示客户')

        # Create orders for some customers
        order_count = 0
        for c in customers:
            if c.funnel_stage in ['成交', '复购', '裂变'] and random.random() > 0.3:
                prod_name = random.choice(list(products.keys()))
                price = products[prod_name]
                qty = random.randint(1, 4)
                total = price * qty

                o = Order(
                    order_id=generate_id('DEMO'),
                    customer_id=c.id,
                    order_date=datetime.utcnow() - timedelta(days=random.randint(1, 45)),
                    order_status=random.choice(['已付款', '已发货', '已签收']),
                    total_amount=total,
                    products=json.dumps([{'name': prod_name, 'qty': qty, 'price': price}]),
                    source=random.choice(['FB广告', 'WhatsApp', '转介绍']),
                )
                db.session.add(o)
                c.total_orders = (c.total_orders or 0) + 1
                c.ltv = (c.ltv or 0) + total
                c.last_order_date = o.order_date
                order_count += 1

                # Sometimes add a second order
                if random.random() > 0.6:
                    prod_name2 = random.choice(list(products.keys()))
                    price2 = products[prod_name2]
                    o2 = Order(
                        order_id=generate_id('DEMO'),
                        customer_id=c.id,
                        order_date=datetime.utcnow() - timedelta(days=random.randint(50, 90)),
                        order_status='已签收',
                        total_amount=price2 * random.randint(1, 3),
                        products=json.dumps([{'name': prod_name2, 'qty': 1, 'price': price2}]),
                        source='复购',
                    )
                    db.session.add(o2)
                    c.total_orders = (c.total_orders or 0) + 1
                    c.ltv = (c.ltv or 0) + o2.total_amount
                    order_count += 1

        db.session.commit()
        print(f'✅ 已创建 {order_count} 笔演示订单')

        # Create some interactions
        for c in customers[:12]:
            i_type = random.choice(['WhatsApp', '电话', 'Messenger'])
            i = Interaction(
                interaction_id=generate_id('DEMO'),
                customer_id=c.id,
                channel=i_type,
                direction='inbound',
                content_summary=f'[DEMO] 客户咨询产品，了解价格和疗效' if random.random() > 0.5 else '[DEMO] 客户反馈使用效果良好',
                timestamp=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            )
            db.session.add(i)
        db.session.commit()
        print(f'✅ 已创建演示互动记录')

        # Create some followups
        for c in customers[5:15]:
            f = FollowUp(
                followup_id=generate_id('DEMO'),
                customer_id=c.id,
                type=random.choice(['复购提醒', '跟进回访', '节日问候']),
                content=f'[DEMO] {c.name} 客户跟进',
                scheduled_at=datetime.utcnow() + timedelta(days=random.randint(1, 14)),
                status=random.choices(['待执行', '已完成'], weights=[7, 3])[0],
            )
            db.session.add(f)
        db.session.commit()
        print(f'✅ 已创建演示跟进任务')

        # Write help file
        help_path = os.path.join(os.path.dirname(__file__), 'DEMO_README.md')
        with open(help_path, 'w', encoding='utf-8') as f:
            f.write(HELP_TEXT.strip())
        print(f'✅ 已生成 DEMO_README.md')

        print('\n🎉 演示数据已加载！打开浏览器查看效果。')
        print('📖 查看 DEMO_README.md 了解更多。')
        print('🗑️  运行 python3 seed_demo.py --clean 可清空演示数据。')

def clean_demo():
    with app.app_context():
        deleted = 0
        for table in [FollowUp, Interaction, Order]:
            items = table.query.all()
            for item in items:
                db.session.delete(item)
                deleted += 1

        customers = Customer.query.filter(Customer.notes.like('%[DEMO]%')).all()
        for c in customers:
            db.session.delete(c)
            deleted += 1
        db.session.commit()

        # Also clean remaining customers with DEMO IDs
        demo_customers = Customer.query.filter(Customer.customer_id.like('DEMO-%')).all()
        for c in demo_customers:
            db.session.delete(c)
            deleted += 1
        db.session.commit()

        print(f'🗑️  已清空 {deleted} 条演示数据')
        print('✅ 现在可以录入真实客户了！')

if __name__ == '__main__':
    if '--clean' in sys.argv:
        clean_demo()
    else:
        seed_demo()
