"""
HK3 CRM — Web Application
Sales Funnel CRM for HK3 Marketing Sdn Bhd
"""
import os, sys, uuid, json
from datetime import datetime, date, timedelta
from dateutil import relativedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'hk3-crm-secret-key-change-in-production'
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
    rfm_segment = db.Column(db.String(20), default='C')
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
RFM_SEGMENTS = ['S（高价值）', 'A（普通老客）', 'B（新客）', 'C（沉睡）']
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
            rfm_segment=request.form.get('rfm_segment', 'B'),
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
    return render_template('customer_form.html', customer=None, stages=FUNNEL_STAGES, rfm_segments=RFM_SEGMENTS)

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
        c.rfm_segment = request.form.get('rfm_segment')
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
    return render_template('customer_form.html', customer=c, stages=FUNNEL_STAGES, rfm_segments=RFM_SEGMENTS)

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

@app.route('/rfm-guide')
def rfm_guide():
    return render_template('rfm_guide.html')

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

# ─── Init DB ─────────────────────────────────────────────────────

def init_db():
    db.create_all()
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
    print(f'📊 打开浏览器访问: http://127.0.0.1:5000')
    app.run(debug=True, host='127.0.0.1', port=5001)
