"""
HK3 CRM — Web Application
Sales Funnel CRM for HK3 Marketing Sdn Bhd
"""
import os, sys, uuid, json, re
from datetime import datetime, date, timedelta
from dateutil import relativedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.secret_key = 'hk3-crm-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'hk3_crm.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ─── Models ──────────────────────────────────────────────────────

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(50))
    phone_whatsapp = db.Column(db.String(20))
    phone_other = db.Column(db.String(20))
    fb_id = db.Column(db.String(50))
    fb_messenger_id = db.Column(db.String(50))
    email = db.Column(db.String(100))
    gender = db.Column(db.String(10))
    age_range = db.Column(db.String(20))
    location_state = db.Column(db.String(50))
    location_city = db.Column(db.String(50))
    shipping_address = db.Column(db.Text)
    language_preference = db.Column(db.String(20), default='中文')
    funnel_stage = db.Column(db.String(20), default='认知')
    stage_updated_at = db.Column(db.DateTime)
    ltv = db.Column(db.Float, default=0)
    total_orders = db.Column(db.Integer, default=0)
    last_order_date = db.Column(db.Date)
    health_concerns = db.Column(db.Text)  # comma-separated
    medication_taking = db.Column(db.Text)
    diabetes_type = db.Column(db.String(50))
    allergies = db.Column(db.Text)
    preferred_courier = db.Column(db.String(50))
    preferred_payment = db.Column(db.String(50))
    preferred_contact_time = db.Column(db.String(50))
    do_not_call = db.Column(db.Boolean, default=False)
    acquisition_source = db.Column(db.String(50))
    acquisition_campaign = db.Column(db.String(50))
    acquisition_date = db.Column(db.Date)
    referrer_customer_id = db.Column(db.String(20))
    last_contact_date = db.Column(db.DateTime)
    last_contact_channel = db.Column(db.String(20))
    total_interactions = db.Column(db.Integer, default=0)
    intent_score = db.Column(db.Integer, default=50)
    engagement_score = db.Column(db.Integer, default=50)
    tags = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))

    orders = db.relationship('Order', backref='customer', lazy=True)
    interactions = db.relationship('Interaction', backref='customer', lazy=True)
    followups = db.relationship('FollowUp', backref='customer', lazy=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    order_status = db.Column(db.String(20), default='待付款')
    total_amount = db.Column(db.Float)
    products = db.Column(db.Text)  # JSON
    discount = db.Column(db.Float, default=0)
    shipping_fee = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(50))
    courier = db.Column(db.String(50))
    tracking_number = db.Column(db.String(50))
    shipping_address = db.Column(db.Text)
    notes = db.Column(db.Text)
    source = db.Column(db.String(50))
    referrer_customer_id = db.Column(db.String(20))

class Interaction(db.Model):
    __tablename__ = 'interactions'
    id = db.Column(db.Integer, primary_key=True)
    interaction_id = db.Column(db.String(20), unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    channel = db.Column(db.String(20))
    direction = db.Column(db.String(10))
    content_summary = db.Column(db.Text)
    full_content_link = db.Column(db.Text)
    attachments = db.Column(db.Text)
    intent = db.Column(db.String(50))
    sentiment = db.Column(db.String(20))
    handled_by = db.Column(db.String(50))
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.DateTime)
    follow_up_notes = db.Column(db.Text)
    ai_analysis = db.Column(db.Text)  # AI 分析结果
    uploaded_chat = db.Column(db.Text)  # 上传的聊天记录（用于AI分析）


class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FollowUp(db.Model):
    __tablename__ = 'followups'
    id = db.Column(db.Integer, primary_key=True)
    followup_id = db.Column(db.String(20), unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    type = db.Column(db.String(30))
    trigger_reason = db.Column(db.Text)
    scheduled_at = db.Column(db.DateTime)
    executed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='待执行')
    content = db.Column(db.Text)
    result = db.Column(db.Text)
    generated_by = db.Column(db.String(50))

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(20), unique=True)
    product_name_en = db.Column(db.String(100))
    product_name_cn = db.Column(db.String(100))
    category = db.Column(db.String(50))
    unit_price = db.Column(db.Float)
    days_per_unit = db.Column(db.Integer)
    reminder_days_before = db.Column(db.Integer, default=20)
    description = db.Column(db.Text)

# ─── Helpers ─────────────────────────────────────────────────────

def generate_id(prefix):
    today = date.today().strftime('%Y%m%d')
    last = Customer.query.filter(Customer.customer_id.like(f'{prefix}-{today}-%')).count() + 1
    return f'{prefix}-{today}-{last:03d}'

FUNNEL_STAGES = ['认知', '兴趣', '询盘', '成交', '复购', '裂变', '流失']
ORDER_STATUSES = ['待付款', '已付款', '已发货', '已签收', '已取消', '退款']

# ─── Routes ──────────────────────────────────────────────────────



@app.route('/customers')
def customer_list():
    q = request.args.get('q', '')
    stage = request.args.get('stage', '')
    page = request.args.get('page', 1, type=int)
    query = Customer.query
    if q:
        query = query.filter(
            db.or_(Customer.name.contains(q), Customer.phone_whatsapp.contains(q),
                   Customer.notes.contains(q))
        )
    if stage:
        query = query.filter_by(funnel_stage=stage)
    customers = query.order_by(Customer.updated_at.desc()).paginate(page=page, per_page=25)
    return render_template('customers.html', customers=customers, q=q, stage=stage, stages=FUNNEL_STAGES)

@app.route('/customers/new', methods=['GET', 'POST'])
def customer_new():
    if request.method == 'POST':
        c = Customer(
            customer_id=generate_id('HK3'),
            name=request.form.get('name'),
            phone_whatsapp=request.form.get('phone_whatsapp'),
            phone_other=request.form.get('phone_other'),
            email=request.form.get('email'),
            gender=request.form.get('gender'),
            location_state=request.form.get('location_state'),
            location_city=request.form.get('location_city'),
            shipping_address=request.form.get('shipping_address'),
            funnel_stage=request.form.get('funnel_stage', '认知'),
            health_concerns=request.form.get('health_concerns'),
            medication_taking=request.form.get('medication_taking'),
            diabetes_type=request.form.get('diabetes_type'),
            allergies=request.form.get('allergies'),
            preferred_courier=request.form.get('preferred_courier'),
            preferred_payment=request.form.get('preferred_payment'),
            acquisition_source=request.form.get('acquisition_source'),
            acquisition_campaign=request.form.get('acquisition_campaign'),
            notes=request.form.get('notes'),
            created_by='WebApp'
        )
        if request.form.get('do_not_call'):
            c.do_not_call = True
        db.session.add(c)
        db.session.commit()
        flash('客户已添加！', 'success')
        return redirect(url_for('customer_detail', id=c.id))
    return render_template('customer_form.html', customer=None, stages=FUNNEL_STAGES)

@app.route('/customers/<int:id>')
def customer_detail(id):
    c = Customer.query.get_or_404(id)
    orders = Order.query.filter_by(customer_id=id).order_by(Order.order_date.desc()).all()
    interactions = Interaction.query.filter_by(customer_id=id).order_by(Interaction.timestamp.desc()).limit(20).all()
    followups = FollowUp.query.filter_by(customer_id=id).order_by(FollowUp.scheduled_at.desc()).all()
    return render_template('customer_detail.html', customer=c, orders=orders,
                           interactions=interactions, followups=followups, stages=FUNNEL_STAGES)

@app.route('/customers/<int:id>/edit', methods=['GET', 'POST'])
def customer_edit(id):
    c = Customer.query.get_or_404(id)
    if request.method == 'POST':
        c.name = request.form.get('name')
        c.nickname = request.form.get('nickname')
        c.phone_whatsapp = request.form.get('phone_whatsapp')
        c.phone_other = request.form.get('phone_other')
        c.email = request.form.get('email')
        c.gender = request.form.get('gender')
        c.location_state = request.form.get('location_state')
        c.location_city = request.form.get('location_city')
        c.shipping_address = request.form.get('shipping_address')
        c.funnel_stage = request.form.get('funnel_stage')
        c.health_concerns = request.form.get('health_concerns')
        c.medication_taking = request.form.get('medication_taking')
        c.diabetes_type = request.form.get('diabetes_type')
        c.allergies = request.form.get('allergies')
        c.preferred_courier = request.form.get('preferred_courier')
        c.preferred_payment = request.form.get('preferred_payment')
        c.do_not_call = bool(request.form.get('do_not_call'))
        c.notes = request.form.get('notes')
        c.tags = request.form.get('tags')
        db.session.commit()
        flash('客户信息已更新！', 'success')
        return redirect(url_for('customer_detail', id=c.id))
    return render_template('customer_form.html', customer=c, stages=FUNNEL_STAGES)

@app.route('/customers/<int:id>/order', methods=['GET', 'POST'])
def customer_add_order(id):
    c = Customer.query.get_or_404(id)
    if request.method == 'POST':
        o = Order(
            order_id=generate_id('ORD'),
            customer_id=id,
            order_date=datetime.strptime(request.form.get('order_date'), '%Y-%m-%d') if request.form.get('order_date') else datetime.utcnow(),
            order_status=request.form.get('order_status', '待付款'),
            total_amount=float(request.form.get('total_amount', 0)),
            products=request.form.get('products'),
            discount=float(request.form.get('discount', 0)),
            shipping_fee=float(request.form.get('shipping_fee', 0)),
            payment_method=request.form.get('payment_method'),
            courier=request.form.get('courier'),
            tracking_number=request.form.get('tracking_number'),
            shipping_address=request.form.get('shipping_address', c.shipping_address),
            notes=request.form.get('notes'),
            source=request.form.get('source', 'WhatsApp')
        )
        db.session.add(o)
        c.total_orders = (c.total_orders or 0) + 1
        c.ltv = (c.ltv or 0) + o.total_amount
        c.last_order_date = o.order_date
        if c.funnel_stage in ['认知', '兴趣', '询盘']:
            c.funnel_stage = '成交'
            c.stage_updated_at = datetime.utcnow()
        db.session.commit()
        flash('订单已添加！', 'success')
        return redirect(url_for('customer_detail', id=id))
    products = Product.query.all()
    return render_template('order_form.html', customer=c, products=products, statuses=ORDER_STATUSES, today=date.today().isoformat())

@app.route('/customers/<int:id>/followup', methods=['POST'])
def customer_add_followup(id):
    c = Customer.query.get_or_404(id)
    f = FollowUp(
        followup_id=generate_id('FLW'),
        customer_id=id,
        type=request.form.get('type', '其他'),
        trigger_reason=request.form.get('trigger_reason'),
        scheduled_at=datetime.strptime(request.form.get('scheduled_at'), '%Y-%m-%d') if request.form.get('scheduled_at') else datetime.utcnow(),
        status='待执行',
        content=request.form.get('content'),
        generated_by='人工'
    )
    db.session.add(f)
    db.session.commit()
    flash('跟进任务已创建！', 'success')
    return redirect(url_for('customer_detail', id=id))

@app.route('/orders/<int:id>/edit', methods=['GET', 'POST'])
def order_edit(id):
    o = Order.query.get_or_404(id)
    c = Customer.query.get_or_404(o.customer_id)
    if request.method == 'POST':
        old_amount = o.total_amount or 0
        o.order_date = datetime.strptime(request.form.get('order_date'), '%Y-%m-%d') if request.form.get('order_date') else o.order_date
        o.order_status = request.form.get('order_status', o.order_status)
        o.total_amount = float(request.form.get('total_amount', 0))
        o.products = request.form.get('products')
        o.discount = float(request.form.get('discount', 0))
        o.shipping_fee = float(request.form.get('shipping_fee', 0))
        o.payment_method = request.form.get('payment_method')
        o.courier = request.form.get('courier')
        o.tracking_number = request.form.get('tracking_number')
        o.shipping_address = request.form.get('shipping_address')
        o.notes = request.form.get('notes')
        o.source = request.form.get('source')
        # Update customer LTV
        c.ltv = (c.ltv or 0) - old_amount + (o.total_amount or 0)
        c.last_order_date = o.order_date
        db.session.commit()
        flash('订单已更新！', 'success')
        return redirect(url_for('customer_detail', id=o.customer_id))
    products = Product.query.all()
    return render_template('order_form.html', customer=c, order=o, products=products, statuses=ORDER_STATUSES, today=date.today().isoformat())

@app.route('/orders/<int:id>/delete', methods=['POST'])
def order_delete(id):
    o = Order.query.get_or_404(id)
    c = Customer.query.get_or_404(o.customer_id)
    cid = o.customer_id
    c.total_orders = max(0, (c.total_orders or 1) - 1)
    c.ltv = max(0, (c.ltv or 0) - (o.total_amount or 0))
    db.session.delete(o)
    db.session.commit()
    flash('订单已删除！', 'success')
    return redirect(url_for('customer_detail', id=cid))

@app.route('/orders')
def order_list():
    page = request.args.get('page', 1, type=int)
    orders = Order.query.order_by(Order.order_date.desc()).paginate(page=page, per_page=25)
    return render_template('orders.html', orders=orders)

@app.route('/followups')
def followup_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = FollowUp.query
    if status:
        query = query.filter_by(status=status)
    followups = query.order_by(FollowUp.scheduled_at.asc()).paginate(page=page, per_page=25)
    return render_template('followups.html', followups=followups, status=status)

@app.route('/followups/<int:id>/complete', methods=['POST'])
def followup_complete(id):
    f = FollowUp.query.get_or_404(id)
    f.status = '已执行'
    f.executed_at = datetime.utcnow()
    f.result = request.form.get('result', '已完成')
    db.session.commit()
    flash('跟进已完成！', 'success')
    return redirect(url_for('followup_list'))

@app.route('/api/funnel_data')
def api_funnel_data():
    stages = FUNNEL_STAGES
    counts = []
    for s in stages:
        counts.append(Customer.query.filter_by(funnel_stage=s).count())
    return jsonify({'stages': stages, 'counts': counts})

@app.route('/api/quick_stats')
def api_quick_stats():
    return jsonify({
        'customers': Customer.query.count(),
        'orders': Order.query.count(),
        'revenue': db.session.query(db.func.sum(Order.total_amount)).scalar() or 0,
        'pending': FollowUp.query.filter_by(status='待执行').count(),
        'today_orders': Order.query.filter(
            db.func.date(Order.order_date) == date.today()
        ).count()
    })

# ─── 复购提醒 ─────────────────────────────────────────────────────

def calc_repurchase_reminders(days_ahead=30):
    """
    计算所有客户的复购提醒。
    基于最近成交订单的产品 + 产品 days_per_unit + 剩余天数。
    """
    reminders = []
    customers = Customer.query.filter(
        Customer.last_order_date.isnot(None),
        Customer.funnel_stage.in_(['成交', '复购'])
    ).all()
    for c in customers:
        recent = Order.query.filter(
            Order.customer_id == c.id,
            Order.order_status.in_(['已付款', '已发货', '已签收'])
        ).order_by(Order.order_date.desc()).first()
        if not recent or not recent.products:
            continue
        try:
            products_data = json.loads(recent.products) if isinstance(recent.products, str) else recent.products
        except:
            continue
        if not isinstance(products_data, list):
            products_data = [products_data]
        start_date = recent.order_date.date() if hasattr(recent.order_date, 'date') else recent.order_date
        for p in products_data:
            pid = p.get('product_id') or p.get('code') or ''
            qty = int(p.get('quantity', 1) or 1)
            product = Product.query.filter(
                db.or_(Product.product_id == pid, Product.product_name_cn.like(f'%{pid}%'))
            ).first()
            if not product or not product.days_per_unit:
                continue
            total_days = product.days_per_unit * qty
            run_out_date = start_date + timedelta(days=total_days)
            remind_date = run_out_date - timedelta(days=product.reminder_days_before)
            days_left = (run_out_date - date.today()).days
            if days_left <= days_ahead:
                reminders.append({
                    'customer_id': c.id,
                    'customer_name': c.name,
                    'phone': c.phone_whatsapp or '',
                    'product': product.product_name_cn,
                    'order_date': start_date.isoformat(),
                    'quantity': qty,
                    'run_out_date': run_out_date.isoformat(),
                    'remind_date': remind_date.isoformat(),
                    'days_left': days_left,
                    'status': '逾期' if days_left < 0 else '即将复购',
                    'funnel_stage': c.funnel_stage,
                })
    reminders.sort(key=lambda r: r['days_left'])
    return reminders

@app.route('/repurchases')
def repurchase_list():
    days_ahead = request.args.get('days', 30, type=int)
    today = date.today()
    
    # Source 1: auto-calculated from orders
    auto_reminders = calc_repurchase_reminders(days_ahead)
    
    # Source 2: FollowUp records imported from Google Sheet
    followup_reminders = []
    followups = FollowUp.query.filter_by(type='复购提醒', status='待执行').all()
    for f in followups:
        if not f.scheduled_at:
            continue
        days_left = (f.scheduled_at.date() - today).days
        if days_left <= days_ahead:
            c = Customer.query.get(f.customer_id)
            followup_reminders.append({
                'customer_id': f.customer_id,
                'customer_name': c.name if c else '?',
                'phone': c.phone_whatsapp or '' if c else '',
                'product': f.trigger_reason.replace('产品预计用完，建议复购（', '').replace('）', '') if f.trigger_reason else '',
                'order_date': '',
                'quantity': '',
                'run_out_date': f.scheduled_at.date().isoformat(),
                'remind_date': f.scheduled_at.date().isoformat(),
                'days_left': days_left,
                'status': '逾期' if days_left < 0 else '即将复购',
                'funnel_stage': c.funnel_stage if c else '',
                'followup_id': f.id,  # for completing
            })
    
    # Merge: auto-calculated takes priority, add followup ones not already covered
    existing_ids = {r['customer_id'] for r in auto_reminders}
    for r in followup_reminders:
        if r['customer_id'] not in existing_ids:
            auto_reminders.append(r)
    
    reminders = sorted(auto_reminders, key=lambda r: r['days_left'])
    overdue = [r for r in reminders if r['status'] == '逾期']
    upcoming = [r for r in reminders if r['status'] == '即将复购']
    return render_template('repurchases.html', reminders=reminders,
                           overdue=overdue, upcoming=upcoming, days_ahead=days_ahead)

@app.route('/api/repurchases')
def api_repurchases():
    today = date.today()
    reminders = []
    
    # Source 1: FollowUp records from Google Sheet
    followups = FollowUp.query.filter_by(type='复购提醒', status='待执行').all()
    for f in followups:
        if not f.scheduled_at:
            continue
        days_left = (f.scheduled_at.date() - today).days
        if days_left <= 30:
            c = Customer.query.get(f.customer_id)
            reminders.append({
                'customer_id': f.customer_id,
                'customer_name': c.name if c else '?',
                'phone': c.phone_whatsapp or '' if c else '',
                'days_left': days_left,
                'status': '逾期' if days_left < 0 else '即将复购',
            })
    
    reminders.sort(key=lambda r: r['days_left'])
    return jsonify({
        'total': len(reminders),
        'overdue': len([r for r in reminders if r['status'] == '逾期']),
        'upcoming': len([r for r in reminders if r['status'] == '即将复购']),
        'reminders': reminders[:20]
    })

# ─── Update dashboard to include repurchase data ────────────────

@app.route('/')
def index():
    total = Customer.query.count()
    by_stage = {}
    for s in FUNNEL_STAGES:
        by_stage[s] = Customer.query.filter_by(funnel_stage=s).count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    total_orders = Order.query.count()
    pending_followups = FollowUp.query.filter_by(status='待执行').count()
    recent_customers = Customer.query.order_by(Customer.updated_at.desc()).limit(10).all()
    # Repurchase data for dashboard (merge FollowUp + auto calc)
    today = date.today()
    followup_reminders = []
    followups = FollowUp.query.filter_by(type='复购提醒', status='待执行').all()
    for f in followups:
        if not f.scheduled_at:
            continue
        days_left = (f.scheduled_at.date() - today).days
        if days_left <= 30:
            c = Customer.query.get(f.customer_id)
            followup_reminders.append({
                'customer_id': f.customer_id,
                'customer_name': c.name if c else '?',
                'phone': c.phone_whatsapp or '' if c else '',
                'product': f.trigger_reason.replace('产品预计用完，建议复购（', '').replace('）', '') if f.trigger_reason else '',
                'days_left': days_left,
                'status': '逾期' if days_left < 0 else '即将复购',
            })
    
    overdue_count = len([r for r in followup_reminders if r['status'] == '逾期'])
    upcoming_reminders = [r for r in followup_reminders if r['status'] == '即将复购'][:8]
    overdue_reminders = [r for r in followup_reminders if r['status'] == '逾期'][:5]
    
    return render_template('index.html', total=total, by_stage=by_stage,
                           total_revenue=total_revenue, total_orders=total_orders,
                           pending_followups=pending_followups, stages=FUNNEL_STAGES,
                           recent_customers=recent_customers,
                           repurchase_reminders=followup_reminders,
                           overdue_count=overdue_count,
                           upcoming_reminders=upcoming_reminders,
                           overdue_reminders=overdue_reminders)

# ─── DeepSeek AI Integration ─────────────────────────────────────

def get_deepseek_api_key():
    """从数据库获取 DeepSeek API key"""
    s = Setting.query.filter_by(key='deepseek_api_key').first()
    return s.value if s else ''

def call_deepseek(prompt, system_prompt='你是HK3 CRM的AI销售助手，擅长分析客户情况并生成跟进建议。请用中文回答。'):
    """调用 DeepSeek API"""
    api_key = get_deepseek_api_key()
    if not api_key:
        return None, '请先在设置页面配置 DeepSeek API Key'
    import urllib.request
    url = 'https://api.deepseek.com/v1/chat/completions'
    payload = json.dumps({
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
        'max_tokens': 2000
    }).encode('utf-8')
    req = urllib.request.Request(url, data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
        method='POST')
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        content = result['choices'][0]['message']['content']
        return content, None
    except Exception as e:
        return None, str(e)

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    if request.method == 'POST':
        key = request.form.get('deepseek_api_key', '').strip()
        # Don't save if it's the masked placeholder '********'
        if key and key != '********':
            s = Setting.query.filter_by(key='deepseek_api_key').first()
            if s:
                s.value = key
            else:
                s = Setting(key='deepseek_api_key', value=key)
                db.session.add(s)
            db.session.commit()
            flash('API Key 已保存！', 'success')
        elif not key:
            flash('请输入 API Key', 'warning')
        else:
            flash('API Key 未变更', 'info')
        return redirect(url_for('settings_page'))
    current_key = get_deepseek_api_key()
    masked = current_key[:8] + '...' + current_key[-4:] if current_key and len(current_key) > 15 else ''
    return render_template('settings.html', has_key=bool(current_key), masked_key=masked)

@app.route('/system/update', methods=['GET', 'POST'])
def system_update():
    import subprocess
    result = None; error = None; git_log = []

    # 获取当前版本（git commit hash）
    current_version = 'local'
    try:
        v = subprocess.run(['git', 'log', '--oneline', '-1'], capture_output=True, text=True, timeout=5, cwd=basedir)
        if v.returncode == 0 and v.stdout.strip():
            current_version = v.stdout.strip()
    except:
        pass

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'check':
            try:
                subprocess.run(['git', 'fetch', 'origin'], capture_output=True, text=True, timeout=15, cwd=basedir)
                r2 = subprocess.run(['git', 'status', '-sb'], capture_output=True, text=True, timeout=10, cwd=basedir)
                log = subprocess.run(['git', 'log', '--oneline', '-5', 'HEAD..origin/main'], capture_output=True, text=True, timeout=10, cwd=basedir)
                if 'behind' in r2.stdout:
                    result = '🔔 有新版本可用！'
                    git_log = [l for l in log.stdout.strip().split('\n') if l]
                else:
                    result = '✅ 当前已是最新版本'
            except Exception as e:
                error = f'检查失败: {e}'
        elif action == 'update':
            try:
                r = subprocess.run(['git', 'pull', 'origin', 'main'], capture_output=True, text=True, timeout=30, cwd=basedir)
                out = r.stdout + r.stderr
                if r.returncode == 0:
                    result = '✅ 更新成功！'
                    if 'requirements.txt' in out:
                        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '-q'], timeout=60, cwd=basedir)
                        result += '\n📦 依赖已更新'
                    result += '\n\n🔄 请重启服务器以应用更新'
                else:
                    error = f'❌ 更新失败\n{out[:800]}'
            except Exception as e:
                error = f'更新失败: {e}'
        elif action == 'restart':
            try:
                subprocess.Popen(['bash', os.path.join(basedir, 'restart.sh')], cwd=basedir)
                return '服务器正在重启... 请稍后刷新页面', 200
            except Exception as e:
                error = f'重启失败: {e}\n请手动重启: python3 app.py'
    return render_template('system.html', result=result, error=error, git_log=git_log, current_version=current_version)

@app.route('/api/ai/analyze/<int:customer_id>', methods=['POST'])
def api_ai_analyze(customer_id):
    """AI分析客户并生成跟进建议"""
    c = Customer.query.get_or_404(customer_id)
    data = request.get_json() or {}
    user_message = data.get('message', '')
    whatsapp_text = data.get('whatsapp_content', '')
    
    # 构建客户信息
    orders = Order.query.filter_by(customer_id=customer_id).order_by(Order.order_date.desc()).limit(5).all()
    order_info = '\n'.join([f"  - {o.order_date.strftime('%Y-%m-%d')}: {o.products or '?'} (RM{o.total_amount or 0}) [{o.order_status}]" for o in orders]) or '  无订单记录'
    followups = FollowUp.query.filter_by(customer_id=customer_id).order_by(FollowUp.scheduled_at.desc()).limit(3).all()
    followup_info = '\n'.join([f"  - {f.type}: {f.content or ''} ({f.status})" for f in followups]) or '  无跟进记录'
    
    prompt = f"""客户信息：
- 姓名：{c.name}
- 电话：{c.phone_whatsapp or '无'}
- 漏斗阶段：{c.funnel_stage}
- 总订单：{c.total_orders or 0}
- 上次购买：{c.last_order_date}
- 累计消费：RM{c.ltv or 0}
- 健康问题：{c.health_concerns or '无'}
- 备注：{c.notes or '无'}

最近订单：
{order_info}

跟进记录：
{followup_info}
"""
    if whatsapp_text:
        prompt += f'\n客户聊天记录：\n{whatsapp_text[:3000]}\n'
    else:
        # 自动从最近互动中找上传的聊天记录
        chats = Interaction.query.filter(
            Interaction.customer_id == customer_id,
            Interaction.uploaded_chat.isnot(None),
            Interaction.uploaded_chat != ''
        ).order_by(Interaction.timestamp.desc()).limit(3).all()
        if chats:
            prompt += '\n客户聊天记录（上次上传）：\n'
            for ch in chats:
                prompt += f'{(ch.uploaded_chat or "")[:2000]}\n---\n'
    if user_message:
        prompt += f'\n用户的问题/要求：\n{user_message}\n'
    else:
        prompt += '\n请分析这位客户的情况，给出跟进建议：1）客户目前的状态 2）建议的跟进策略 3）建议的话术/信息 4）适合的优惠或产品推荐。'
    
    result, err = call_deepseek(prompt)
    if err:
        return jsonify({'ok': False, 'error': err})
    return jsonify({'ok': True, 'result': result})

@app.route('/api/ai/chat/<int:customer_id>', methods=['POST'])
def api_ai_chat(customer_id):
    """AI聊天接口（DeepSeek）"""
    c = Customer.query.get_or_404(customer_id)
    data = request.get_json() or {}
    user_message = data.get('message', '')
    history = data.get('history', [])
    
    if not user_message:
        return jsonify({'ok': False, 'error': '请输入消息'})
    
    # 构建客户上下文
    orders = Order.query.filter_by(customer_id=customer_id).order_by(Order.order_date.desc()).limit(5).all()
    order_info = '\n'.join([f"  - {o.order_date.strftime('%Y-%m-%d')}: {o.products or '?'} (RM{o.total_amount or 0})" for o in orders]) or '无'
    interactions = Interaction.query.filter_by(customer_id=customer_id).order_by(Interaction.timestamp.desc()).limit(5).all()
    chat_info = '\n'.join([f"  - [{i.channel}] {i.content_summary or ''}" for i in interactions]) or '无'
    # Also get uploaded chat records
    uploaded = Interaction.query.filter(
        Interaction.customer_id == customer_id,
        Interaction.uploaded_chat.isnot(None),
        Interaction.uploaded_chat != ''
    ).order_by(Interaction.timestamp.desc()).first()
    
    system_prompt = f"""你是HK3 CRM的AI销售助手，专门帮助分析客户和生成跟进方案。
当前正在查看的客户信息：
- 姓名：{c.name}
- 电话：{c.phone_whatsapp or '无'}
- 漏斗阶段：{c.funnel_stage}
- 总订单：{c.total_orders or 0}
- 上次购买：{c.last_order_date}
- LTV：RM{c.ltv or 0}
- 健康问题：{c.health_concerns or '无'}
- 备注：{c.notes or '无'}

最近订单：
{order_info}

互动记录：
{chat_info}

你正在帮销售员分析与这个客户的沟通策略。请用中文回答，简短实用。"""
    if uploaded:
        system_prompt += f'\n\n客户上传的聊天记录：\n{(uploaded.uploaded_chat or "")[:3000]}'
    
    messages = [{'role': 'system', 'content': system_prompt}]
    for h in history[-10:]:
        messages.append({'role': h.get('role', 'user'), 'content': h.get('content', '')})
    messages.append({'role': 'user', 'content': user_message})
    
    import urllib.request
    api_key = get_deepseek_api_key()
    if not api_key:
        return jsonify({'ok': False, 'error': '请先配置 DeepSeek API Key'})
    
    url = 'https://api.deepseek.com/v1/chat/completions'
    payload = json.dumps({
        'model': 'deepseek-chat',
        'messages': messages,
        'temperature': 0.7,
        'max_tokens': 2000
    }).encode('utf-8')
    req = urllib.request.Request(url, data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
        method='POST')
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        content = result['choices'][0]['message']['content']
        return jsonify({'ok': True, 'result': content})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/customers/<int:id>/ai')
def customer_ai_chat(id):
    c = Customer.query.get_or_404(id)
    orders = Order.query.filter_by(customer_id=id).order_by(Order.order_date.desc()).all()
    interactions = Interaction.query.filter_by(customer_id=id).order_by(Interaction.timestamp.desc()).limit(50).all()
    followups = FollowUp.query.filter_by(customer_id=id).order_by(FollowUp.scheduled_at.desc()).all()
    has_api_key = bool(get_deepseek_api_key())
    return render_template('ai_chat.html', customer=c, orders=orders,
                           interactions=interactions, followups=followups, has_api_key=has_api_key)

@app.route('/customers/<int:id>/upload-chat', methods=['POST'])
def customer_upload_chat(id):
    """上传聊天记录文件，存入 Interaction"""
    c = Customer.query.get_or_404(id)
    content = ''
    filename = ''

    # 方式1：上传文件（.txt 或 WhatsApp 导出的 .zip）
    if 'file' in request.files:
        f = request.files['file']
        if f.filename:
            filename = f.filename
            raw = f.read()
            if filename.lower().endswith('.zip'):
                # WhatsApp 导出格式：解压找 _chat.txt
                import zipfile, io
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    chat_files = [n for n in z.namelist() if n.endswith('_chat.txt')]
                    if chat_files:
                        content = z.read(chat_files[0]).decode('utf-8', errors='replace')
                    else:
                        content = '⚠️ ZIP 文件中未找到 _chat.txt'
            else:
                content = raw.decode('utf-8', errors='replace')

    # 方式2：直接粘贴文本
    if not content:
        content = request.form.get('chat_content', '').strip()

    if not content:
        flash('请上传文件或粘贴聊天内容', 'warning')
        return redirect(url_for('customer_detail', id=id))

    summary = content[:150] + '...' if len(content) > 150 else content

    interaction = Interaction(
        interaction_id=generate_id('CHAT'),
        customer_id=id,
        channel='聊天记录',
        direction='inbound',
        content_summary=f'📄 {filename or "粘贴文本"}: {summary}',
        uploaded_chat=content,
    )
    db.session.add(interaction)
    c.last_contact_channel = '上传聊天'
    c.last_contact_date = datetime.utcnow()
    c.total_interactions = (c.total_interactions or 0) + 1
    db.session.commit()

    flash('✅ 聊天记录已上传！AI 分析时会参考这些内容。', 'success')
    return redirect(url_for('customer_detail', id=id))

@app.route('/customers/<int:id>/delete-chat/<int:interaction_id>', methods=['POST'])
def customer_delete_chat(id, interaction_id):
    """删除已上传的聊天记录"""
    i = Interaction.query.get_or_404(interaction_id)
    if i.customer_id != id:
        flash('操作无效', 'error')
        return redirect(url_for('customer_detail', id=id))
    db.session.delete(i)
    db.session.commit()
    flash('🗑️ 聊天记录已删除', 'success')
    return redirect(url_for('customer_detail', id=id))

# ─── Schema Migration ────────────────────────────────────────
SCHEMA_VERSION = 2

def get_schema_version():
    """Return current schema version from DB"""
    s = Setting.query.filter_by(key='schema_version').first()
    return int(s.value) if s else 0

def set_schema_version(ver):
    s = Setting.query.filter_by(key='schema_version').first()
    if s:
        s.value = str(ver)
    else:
        s = Setting(key='schema_version', value=str(ver))
        db.session.add(s)
    db.session.commit()

def run_migrations():
    """Run pending migrations. Add new migration functions here as we increment SCHEMA_VERSION."""
    current = get_schema_version()
    target = SCHEMA_VERSION

    if current >= target:
        return

    print(f'🔄 数据库迁移: v{current} → v{target}')

    # ---- Add new migrations below ----
    if current < 2:
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE interactions ADD COLUMN uploaded_chat TEXT'))
        print('  ✅ v2: interactions.uploaded_chat')

    # When version X released, agent pulls code, migration auto-runs, data preserved

    set_schema_version(target)
    print(f'✅ 数据库已更新至 v{target}')

def init_db():
    db.create_all()
    run_migrations()
    if Product.query.count() == 0:
        products = [
            Product(product_id='P001', product_name_en='Bamboo Salt Coffee (Sugar-Free)', product_name_cn='竹盐咖啡（无糖版）', category='咖啡/控糖', unit_price=45.0, days_per_unit=20, reminder_days_before=20),
            Product(product_id='P002', product_name_en='Bamboo Salt 3x', product_name_cn='3x竹盐', category='竹盐', unit_price=28.0, days_per_unit=30, reminder_days_before=20),
            Product(product_id='P003', product_name_en='Bamboo Salt 9x', product_name_cn='9x竹盐（药用级）', category='竹盐', unit_price=68.0, days_per_unit=30, reminder_days_before=20),
            Product(product_id='P004', product_name_en='GlucoDNA', product_name_cn='GlucoDNA 基因护肾', category='保健品/肾脏', unit_price=188.0, days_per_unit=15, reminder_days_before=15),
            Product(product_id='P005', product_name_en='Glucoless', product_name_cn='去糖灵', category='保健品/控糖', unit_price=128.0, days_per_unit=15, reminder_days_before=15),
            Product(product_id='P006', product_name_en='Cardio Xupport', product_name_cn='Cardio Xupport', category='保健品/心脏', unit_price=128.0, days_per_unit=30, reminder_days_before=20),
            Product(product_id='P007', product_name_en='RespVit', product_name_cn='RespVit 呼吸配方', category='保健品/呼吸', unit_price=98.0, days_per_unit=30, reminder_days_before=20),
            Product(product_id='P008', product_name_en='Purple Bamboo Salt', product_name_cn='紫竹盐', category='竹盐', unit_price=48.0, days_per_unit=30, reminder_days_before=20),
        ]
        db.session.add_all(products)
        db.session.commit()
        print('✅ Products seeded')

if __name__ == '__main__':
    with app.app_context():
        init_db()
    print('🚀 HK3 CRM 启动中...')
    print('📊 http://127.0.0.1:5001')
    app.run(debug=True, host='127.0.0.1', port=5001)
