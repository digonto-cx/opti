import os
import datetime
import random
import urllib.request
import urllib.parse
import json
import base64
import math
import re
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from supabase import create_client, Client
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "opti_work_secured_stable_permanent_key_998124")
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=30)

# ==========================================
# VERCEL SERVERLESS SAFE SUPABASE DRIVER
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "YOUR_SUPABASE_KEY")

class SafeSupabaseProxy:
    """
    Vercel-এ HTTP/2 Server Disconnected রোধের জন্য
    ডায়নামিক সকেট অটো-রিকানেক্টর প্রক্সি
    """
    def __init__(self, url, key):
        self.url = url
        self.key = key
        self._client = None

    def get_client(self) -> Client:
        # প্রতিবার সতেজ ক্লায়েন্ট নিশ্চিতকরণ
        try:
            if self._client is None:
                self._client = create_client(self.url, self.key)
        except Exception:
            self._client = create_client(self.url, self.key)
        return self._client

    def table(self, table_name: str):
        try:
            return self.get_client().table(table_name)
        except Exception:
            self._client = create_client(self.url, self.key)
            return self._client.table(table_name)

    def rpc(self, func_name: str, params: dict):
        try:
            return self.get_client().rpc(func_name, params)
        except Exception:
            self._client = create_client(self.url, self.key)
            return self._client.rpc(func_name, params)

# গ্লোবাল supabase ভেরিয়েবল হিসেবে এই প্রক্সিটি কাজ করবে (অন্য কোনো পেজের কোড বদলাতে হবে না)
supabase = SafeSupabaseProxy(SUPABASE_URL, SUPABASE_KEY)


def send_telegram_notification(text):
    token = "8922254680:AAEwgygDXJl0xjB9TPX-Rl0XeVAfVobQdXI"
    chat_id = "@ortipay"
    
    if token == "YOUR_BOT_TOKEN" or chat_id == "@your_channel_username":
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "Main Channel 📢", "url": "https://t.me/ortiwokr"},
                {"text": "Support Help 🤖", "url": "https://t.me/Optiworkhelp"}
            ]
        ]
    }
    
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(reply_markup)
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req)
    except Exception as e:
        print("Telegram API Error:", e)


def generate_fake_phone():
    prefixes = ['017', '019', '018', '015', '016', '013', '014']
    prefix = random.choice(prefixes)
    suffix = random.randint(100, 999)
    return f"{prefix}*****{suffix}"


def round_to_nearest_5(num):
    return round(num / 5) * 5


def generate_deposit_amount():
    roll = random.random()
    if roll < 0.75:
        amount = random.randint(100, 499)
    else:
        amount = random.randint(500, 1000)
    return float(round_to_nearest_5(amount))


def generate_withdraw_amount():
    roll = random.random()
    if roll < 0.10:
        amount = random.randint(300, 400)
    elif roll < 0.85:
        amount = random.randint(405, 999)
    else:
        amount = random.randint(1000, 2000)
    return float(round_to_nearest_5(amount))



@app.route('/api/cron/simulate-traffic', methods=['GET'])
def simulate_traffic_cron():
    cron_key = request.args.get('key')
    if cron_key != os.environ.get("CRON_SECRET_KEY", "secure_cron_key_123"):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    now = datetime.datetime.now(datetime.timezone.utc)
    
    due_success_tx = supabase.table("simulated_transactions") \
        .select("*") \
        .eq("status", "Pending") \
        .lte("scheduled_success_at", now.isoformat()) \
        .execute().data
        
    if not due_success_tx:
        for _ in range(random.randint(2, 3)):
            fake_uid = random.randint(1000, 6891)
            fake_phone = generate_fake_phone()
            method = random.choice(['bKash', 'Nagad'])
            tx_type = random.choice(['Deposit', 'Withdraw'])
            amount = generate_withdraw_amount() if tx_type == 'Withdraw' else generate_deposit_amount()
            
            supabase.table("simulated_transactions").insert({
                "uid": fake_uid,
                "phone_number": fake_phone,
                "amount": amount,
                "method": method,
                "type": tx_type,
                "status": "Success",
                "scheduled_success_at": now.isoformat()
            }).execute()
            
            success_msg = f"""<b>✅ {tx_type.upper()} SUCCESSFUL</b>
────────────────────
<b>User UID:</b> <code>#{fake_uid}</code>
<b>Amount:</b> ৳ {amount}
<b>Gateway:</b> {method}
<b>Number:</b> {fake_phone}
<b>Status:</b> 🟢 Completed (Success)
────────────────────
<i>Payout processed via Automated Node!</i>"""
            send_telegram_notification(success_msg)
    else:
        for tx in due_success_tx:
            if tx['type'] == 'Withdraw' and random.random() < 0.02:
                supabase.table("simulated_transactions").update({"status": "Rejected"}).eq("id", tx['id']).execute()
                
                reject_msg = f"""<b>❌ WITHDRAWAL REJECTED</b>
────────────────────
<b>User UID:</b> <code>#{tx['uid']}</code>
<b>Amount:</b> ৳ {tx['amount']}
<b>Gateway:</b> {tx['method']}
<b>Number:</b> {tx['phone_number']}
<b>Status:</b> 🔴 Rejected / Verification Failed
────────────────────
<i>Transaction declined by Automated Security System.</i>"""
                send_telegram_notification(reject_msg)
            else:
                supabase.table("simulated_transactions").update({"status": "Success"}).eq("id", tx['id']).execute()
                
                success_msg = f"""<b>✅ {tx['type'].upper()} SUCCESSFUL</b>
────────────────────
<b>User UID:</b> <code>#{tx['uid']}</code>
<b>Amount:</b> ৳ {tx['amount']}
<b>Gateway:</b> {tx['method']}
<b>Number:</b> {tx['phone_number']}
<b>Status:</b> 🟢 Completed (Success)
────────────────────
<i>Payout processed via Automated Node!</i>"""
                send_telegram_notification(success_msg)

    num_of_pending = random.randint(3, 4)
    for _ in range(num_of_pending):
        fake_uid = random.randint(1000, 6891)
        fake_phone = generate_fake_phone()
        method = random.choice(['bKash', 'Nagad'])
        
        if random.random() < 0.60:
            tx_type = 'Withdraw'
            amount = generate_withdraw_amount()
        else:
            tx_type = 'Deposit'
            amount = generate_deposit_amount()
            
        random_delay_minutes = random.randint(180, 240)
        scheduled_success = now + datetime.timedelta(minutes=random_delay_minutes)
        
        supabase.table("simulated_transactions").insert({
            "uid": fake_uid,
            "phone_number": fake_phone,
            "amount": amount,
            "method": method,
            "type": tx_type,
            "status": "Pending",
            "scheduled_success_at": scheduled_success.isoformat()
        }).execute()
        
        pending_msg = f"""<b>🚨 NEW {tx_type.upper()} REQUEST</b>
────────────────────
<b>User UID:</b> <code>#{fake_uid}</code>
<b>Amount:</b> ৳ {amount}
<b>Gateway:</b> {method}
<b>Number:</b> {fake_phone}
<b>Status:</b> 🟡 Pending (Processing)
────────────────────
<i>Request queued on Mining Server...</i>"""
        send_telegram_notification(pending_msg)
        
    return jsonify({"status": "completed", "instant_payouts_and_pendings_created": True}), 200


def mask_email(email):
    try:
        parts = email.split('@')
        name, domain = parts[0], parts[1]
        if len(name) > 3:
            return f"{name[:2]}***{name[-1]}@{domain}"
        return f"{name[0]}***@{domain}"
    except Exception:
        return "u***@email.com"

app.jinja_env.filters['mask_email'] = mask_email


def check_admin_auth():
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = supabase.table("users").select("is_admin, is_banned").eq("id", user_id).execute().data
    if user and user[0]['is_admin'] and not user[0]['is_banned']:
        return user_id
    return None


# (অন্যান্য কোড অপরিবর্তিত থাকবে, app.py ফাইলের একদম ওপরের দিকে import math যুক্ত করে নিন এবং admin_dashboard রাউটটি নিচের কোড দ্বারা পরিবর্তন করুন)


def require_activation(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
            
        # ইউজারের এক্টিভেশন স্ট্যাটাস চেক
        try:
            u_res = supabase.table("users").select("is_activated").eq("id", user_id).execute().data
            if not u_res or not u_res[0].get('is_activated'):
                flash("এই পেজে প্রবেশ করতে প্রথমে আপনার অ্যাকাউন্টটি সচল (Activate) করুন।", "danger")
                return redirect(url_for('activate'))
        except Exception:
            return redirect(url_for('activate'))
            
        return f(*args, **kwargs)
    return decorated_function
    
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    now = datetime.datetime.now(datetime.timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    all_users = supabase.table("users").select("id", count="exact").execute()
    total_users = all_users.count if all_users.count is not None else 0
    
    today_users_query = supabase.table("users").select("id", count="exact").gte("created_at", today_start).execute()
    today_users = today_users_query.count if today_users_query.count is not None else 0
    
    total_dep_query = supabase.table("deposits").select("amount").eq("status", "Approved").execute().data
    total_deposits = sum(float(d['amount']) for d in total_dep_query)
    
    today_dep_query = supabase.table("deposits").select("amount").eq("status", "Approved").gte("created_at", today_start).execute().data
    today_deposits = sum(float(d['amount']) for d in today_dep_query)
    
    pending_dep_res = supabase.table("deposits").select("id", count="exact").eq("status", "Pending").execute()
    pending_deposits_count = pending_dep_res.count if pending_dep_res.count is not None else 0
    
    pending_with_res = supabase.table("withdrawals").select("id", count="exact").eq("status", "Pending").execute()
    pending_withdrawals_count = pending_with_res.count if pending_with_res.count is not None else 0
    
    pending_tasks_res = supabase.table("task_submissions").select("id", count="exact").eq("status", "Pending").execute()
    pending_tasks_count = pending_tasks_res.count if pending_tasks_res.count is not None else 0
    
    # --- পেজিনেশন ক্যালকুলেশন (২০ জন করে প্রতি পেজে) ---
    page = int(request.args.get('page', 1))
    limit = 20
    start = (page - 1) * limit
    end = start + limit - 1
    
    search_query = request.args.get('search', '').strip()
    users_list = []
    
    if search_query:
        # সার্চ করা হলে ফিল্টার করা ইউজার তালিকা এবং পেজিনেশন রেঞ্জ লিমিট
        query_builder = supabase.table("users").select("id, uid, username, email, balance, is_banned, device_name")
        
        if search_query.isdigit():
            u_res = query_builder.eq("uid", int(search_query)).range(start, end).execute()
        else:
            u_res = query_builder.or_(f"email.ilike.%{search_query}%,username.ilike.%{search_query}%").range(start, end).execute()
            
        users_list = u_res.data or []
        has_next = len(users_list) == limit
        has_prev = page > 1
    else:
        # ডিফল্টভাবে সমস্ত ইউজারদের মেম্বার তালিকা পেজিনেশন রেঞ্জ লিমিট সহ
        u_res = supabase.table("users").select("id, uid, username, email, balance, is_banned, device_name") \
            .order("created_at", desc=True).range(start, end).execute()
            
        users_list = u_res.data or []
        total_pages = math.ceil(total_users / limit)
        has_next = page < total_pages
        has_prev = page > 1

    return render_template('admin.html', 
                           total_users=total_users, 
                           today_users=today_users, 
                           total_deposits=total_deposits, 
                           today_deposits=today_deposits, 
                           pending_deposits_count=pending_deposits_count,
                           pending_withdrawals_count=pending_withdrawals_count,
                           pending_tasks_count=pending_tasks_count,
                           users_list=users_list,
                           search_query=search_query,
                           page=page,
                           has_next=has_next,
                           has_prev=has_prev)
    
# (অন্যান্য এডমিন রাউটের সাথে নিচের সংশোধিত রাউটটি যুক্ত করুন)

# app.py ফাইলের একদম নিচে এই এরর হ্যান্ডলার রাউট দুটি যুক্ত করুন:

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# (অন্যান্য কোডের সাথে নিচের নতুন অ্যাকাউন্ট অ্যাক্টিভেশন রাউটগুলো যুক্ত করুন)

# ==========================================
# REPORT / FEEDBACK TO ADMIN ROUTE
# ==========================================
@app.route('/report', methods=['GET', 'POST'])
def user_report_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user_res = supabase.table("users").select("*").eq("id", user_id).execute().data
    if not user_res:
        session.clear()
        return redirect(url_for('login'))
        
    user = user_res[0]
    
    # ইউজারের পূর্ববর্তী রিপোর্ট চেক
    existing_report = None
    try:
        report_res = supabase.table("user_reports") \
            .select("*").eq("user_id", user_id) \
            .order("created_at", desc=True).execute().data
        if report_res:
            existing_report = report_res[0]
    except Exception as e:
        print("Report Fetch Error:", e)

    # ডাইনামিক সময়-ভিত্তিক স্ট্যাটাস ক্যালকুলেশন
    dynamic_status = "Pending"
    status_step = 1
    
    if existing_report:
        try:
            created_at = datetime.datetime.fromisoformat(existing_report['created_at'].replace('Z', '+00:00'))
            now = datetime.datetime.now(datetime.timezone.utc)
            diff_hours = (now - created_at).total_seconds() / 3600.0

            if diff_hours >= 10:
                dynamic_status = "এডমিন আপনাকে কল করবেন"
                status_step = 4
            elif diff_hours >= 4:
                dynamic_status = "এডমিন দেখেছেন"
                status_step = 3
            elif diff_hours >= 2:
                dynamic_status = "Under Review (পর্যালোচনা চলছে)"
                status_step = 2
            else:
                dynamic_status = "Pending (অপেক্ষমান)"
                status_step = 1
        except Exception:
            pass

    if request.method == 'POST':
        if existing_report:
            flash("আপনি ইতিমধ্যে একটি রিপোর্ট জমা দিয়েছেন। নতুন রিপোর্ট জমা দেওয়া যাবে না।", "danger")
            return redirect(url_for('user_report_page'))
            
        nagad_number = str(request.form.get('nagad_number', '')).strip()
        feedback_text = str(request.form.get('feedback_text', '')).strip()
        
        if not nagad_number or not feedback_text:
            flash("দয়া করে নগদ নম্বর এবং সমস্যার বিবরণ লিখুন।", "danger")
            return redirect(url_for('user_report_page'))
            
        try:
            supabase.table("user_reports").insert({
                "user_id": user_id,
                "username": user.get('username'),
                "email": user.get('email'),
                "uid": user.get('uid'),
                "balance": float(user.get('balance', 0)),
                "nagad_number": nagad_number,
                "feedback_text": feedback_text
            }).execute()
            flash("আপনার রিপোর্টটি সফলভাবে জমা হয়েছে। এডমিন দ্রুত ব্যবস্থা গ্রহণ করবে।", "success")
            return redirect(url_for('user_report_page'))
        except Exception as e:
            print("Report Submit Error:", e)
            flash("রিপোর্ট জমা দিতে সমস্যা হয়েছে। আবার চেষ্টা করুন।", "danger")
            return redirect(url_for('user_report_page'))

    return render_template('report.html', 
                           user=user, 
                           existing_report=existing_report, 
                           dynamic_status=dynamic_status,
                           status_step=status_step)


# ১. মেম্বার প্যানেল অ্যাকাউন্ট অ্যাক্টিভেশন রাউট (/activate)
@app.route('/activate', methods=['GET', 'POST'])
def activate():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    # ইউজার অলরেডি এক্টিভেটেড হলে সরাসরি ড্যাশবোর্ডে রিডাইরেক্ট করবে
    if user.get('is_activated'):
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        method = request.form.get('method')
        number = request.form.get('number')
        tx_id = request.form.get('transaction_id')
        
        try:
            supabase.table("activations").insert({
                "user_id": user_id,
                "payment_method": method,
                "payment_number": number,
                "transaction_id": tx_id.strip(),
                "status": "Pending"
            }).execute()
            flash("অ্যাক্টিভেশন অনুরোধ সফলভাবে জমা হয়েছে। এডমিন দ্রুত এটি সক্রিয় করে দেবে।", "success")
            return redirect(url_for('activate'))
        except Exception:
            flash("এই ট্রানজেকশন আইডিটি পূর্বে ব্যবহৃত হয়েছে।", "danger")
            
    # পেন্ডিং বা রিজেক্টেড রিকোয়েস্টের স্ট্যাটাস ট্র্যাকিং
    sub_query = supabase.table("activations").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    status = sub_query[0]['status'] if sub_query else None
    
    return render_template('activate.html', user=user, status=status)


# ২. এডমিন প্যানেল অ্যাকাউন্ট অ্যাক্টিভেশন ম্যানেজমেন্ট রাউট (/admin/activations)
@app.route('/admin/activations')
def admin_activations():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    pending = supabase.table("activations") \
        .select("*, users:user_id(username, email, uid)") \
        .eq("status", "Pending") \
        .order("created_at", desc=True).execute().data or []
        
    return render_template('admin_activations.html', pending_activations=pending)


# ৩. এডমিন অ্যাক্টিভেশন এপ্রুভ/রিজেক্ট অ্যাকশন রাউট
@app.route('/admin/activate-action', methods=['POST'])
def admin_activate_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    activation_id = request.form.get('activation_id')
    action = request.form.get('action') # 'approve' or 'reject'
    
    act_query = supabase.table("activations").select("*").eq("id", activation_id).execute().data
    if not act_query:
        flash("রেকর্ড পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_activations'))
        
    act = act_query[0]
    target_user_id = act['user_id']
    
    if action == 'approve':
        # ১. পেমেন্ট এপ্রুভ করা
        supabase.table("activations").update({"status": "Approved"}).eq("id", activation_id).execute()
        # ২. ইউজারের অ্যাকাউন্ট এক্টিভ বা ট্রু (True) করে দেওয়া
        supabase.table("users").update({"is_activated": True}).eq("id", target_user_id).execute()
        
        # ৩. ৪0 টাকা এক্টিভেশন ফি লগে মাইনাস ভ্যালু আকারে সেভ করা
        supabase.table("transactions").insert({
            "user_id": target_user_id,
            "title": "Account Activated Successfully (৳40 fee)",
            "amount": -40.00
        }).execute()
        
        flash("ইউজার অ্যাকাউন্ট সফলভাবে অ্যাক্টিভ বা সচল করা হয়েছে।", "success")
    elif action == 'reject':
        supabase.table("activations").update({"status": "Rejected"}).eq("id", activation_id).execute()
        flash("অ্যাক্টিভেশন পেমেন্ট রিকোয়েস্ট বাতিল করা হয়েছে।", "success")
        
    return redirect(url_for('admin_activations'))
    
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
    
@app.route('/admin/payout')
def admin_payout_generator():
    if not check_admin_auth():
        flash("আপনার এডমিন প্যানেলে প্রবেশের অনুমতি নেই।", "danger")
        return redirect(url_for('login'))
        
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    five_hours_ago = (now_utc - datetime.timedelta(hours=5)).isoformat()
    
    # ১. বিগত ৫ ঘণ্টার রিয়াল উইথড্রয়াল ডাটা নিরাপদ কুয়েরি
    try:
        real_w_res = supabase.table("withdrawals") \
            .select("amount, status, user_id") \
            .neq("status", "Pending") \
            .gte("created_at", five_hours_ago).execute()
        real_w = real_w_res.data or []
    except Exception as e:
        print("Real Withdraw Fetch Error:", e)
        real_w = []
        
    # ২. বিগত ৫ ঘণ্টার ফেক/সিমুলেটেড উইথড্রয়াল ডাটা নিরাপদ কুয়েরি
    try:
        fake_w_res = supabase.table("simulated_transactions") \
            .select("amount, status, uid") \
            .eq("type", "Withdraw") \
            .neq("status", "Pending") \
            .gte("created_at", five_hours_ago).execute()
        fake_w = fake_w_res.data or []
    except Exception as e:
        print("Fake Withdraw Fetch Error:", e)
        fake_w = []
        
    # ৩. সফল ও বাতিল পেমেন্ট ফিল্টারিং
    success_real = [w for w in real_w if w.get('status') == 'Approved']
    success_fake = [fw for fw in fake_w if fw.get('status') == 'Success']
    
    rejected_real = [w for w in real_w if w.get('status') == 'Rejected']
    rejected_fake = [fw for fw in fake_w if fw.get('status') == 'Rejected']
    
    # ৪. টোটাল সফল ও বাতিল হিসাব (NoneType মুক্ত নিরাপদ সামেশন)
    def safe_sum(item_list):
        total = 0.0
        for item in item_list:
            try:
                total += float(item.get('amount', 0))
            except (ValueError, TypeError):
                pass
        return total

    total_success_amount = safe_sum(success_real) + safe_sum(success_fake)
    total_success_count = len(success_real) + len(success_fake)
    
    total_rejected_amount = safe_sum(rejected_real) + safe_sum(rejected_fake)
    total_rejected_count = len(rejected_real) + len(rejected_fake)
    
    # বাংলাদেশ সময় জেনারেশন (UTC+6)
    now_bd = now_utc + datetime.timedelta(hours=6)
    generation_time = now_bd.strftime("%d %b %Y, %I:%M %p")
    
    return render_template('admin_payout.html',
                           total_success_amount=round(total_success_amount, 2),
                           total_success_count=total_success_count,
                           total_rejected_amount=round(total_rejected_amount, 2),
                           total_rejected_count=total_rejected_count,
                           generation_time=generation_time)

# ১. ইউজার জিমেইল সাবমিশন পেজ রাউট (/gmails)
@app.route('/gmails', methods=['GET', 'POST'])
def gmail_tasks():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    try:
        user_res = supabase.table("users").select("*").eq("id", user_id).execute().data
        if not user_res:
            session.clear()
            return redirect(url_for('login'))
        user = user_res[0]
    except Exception as e:
        print("User Fetch Error on Gmails:", e)
        session.clear()
        return redirect(url_for('login'))
        
    user_registered_email = str(user.get('email', '')).strip().lower()
    
    # ডাটাবেজ সেটিংস থেকে লাইভ জিমেইল রেট রিট্রিভ
    try:
        price_res = supabase.table("settings").select("value").eq("key", "gmail_price").execute().data
        gmail_price = float(price_res[0]['value']) if price_res else 15.00
    except Exception:
        gmail_price = 15.00
    
    if request.method == 'POST':
        email_input = str(request.form.get('gmail_address', '')).strip().lower()
        pass_input = str(request.form.get('gmail_password', '')).strip()
        
        if not email_input or not pass_input:
            flash("দয়া করে জিমেইল এবং পাসওয়ার্ড দুটিই সঠিকভাবে ইনপুট দিন।", "danger")
            return redirect(url_for('gmail_tasks'))
            
        # ১. সিকিউরিটি চেক: নিজস্ব রেজিস্ট্রেশন ইমেইল সাবমিট করা নিষিদ্ধ
        if email_input == user_registered_email:
            flash("নিরাপত্তা সতর্কতা: আপনার নিজস্ব একাউন্ট খোলার ইমেইলটি বিক্রয়ের জন্য জমা দেওয়া যাবে না। অনুগ্রহ করে নতুন ফ্রেশ জিমেইল দিন।", "danger")
            return redirect(url_for('gmail_tasks'))
            
        # ২. সিকিউরিটি চেক: একই জিমেইল পূর্বে ডাটাবেজে জমা পড়েছে কিনা
        try:
            duplicate_check = supabase.table("gmail_submissions") \
                .select("id") \
                .eq("email", email_input).execute().data
                
            if duplicate_check:
                flash("এই জিমেইল অ্যাকাউন্টটি ইতিমধ্যে পূর্বে সাবমিট করা হয়েছে। অনুগ্রহ করে সম্পূর্ণ নতুন জিমেইল দিন।", "danger")
                return redirect(url_for('gmail_tasks'))
        except Exception as e:
            print("Duplicate Gmail Check Error:", e)

        # ৩. সফল ডাটাবেজ ইনসার্ট
        try:
            supabase.table("gmail_submissions").insert({
                "user_id": user_id,
                "email": email_input,
                "password": pass_input,
                "price": gmail_price, # সাবমিটের সময়ের রেট লক থাকবে
                "status": "Pending"
            }).execute()
            flash("জিমেইল অ্যাকাউন্টটি সফলভাবে জমা দেওয়া হয়েছে! এডমিন ভেরিফাই করে ওয়ালেটে টাকা যোগ করবে।", "success")
            return redirect(url_for('gmail_tasks'))
        except Exception as insert_err:
            print("Gmail Insert Error:", insert_err)
            flash("জিমেইল সাবমিট করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।", "danger")
            
    # এই ইউজারের পূর্ববর্তী জিমেইল সাবমিশন হিস্ট্রি রিট্রিভ
    submissions = []
    try:
        submissions = supabase.table("gmail_submissions") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True).execute().data or []
    except Exception as fetch_err:
        print("Gmail History Fetch Error:", fetch_err)
        submissions = []
        
    return render_template('gmails.html', user=user, gmail_price=gmail_price, submissions=submissions)
    
# ২. এডমিন জিমেইল রিভিউ ও রেট পরিবর্তনের পেজ রাউট (/admin/gmails)
@app.route('/admin/gmails', methods=['GET', 'POST'])
def admin_gmails():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    # রেট আপডেট ফরম হ্যান্ডলিং
    if request.method == 'POST':
        new_price = request.form.get('new_price')
        if new_price:
            supabase.table("settings").upsert({"key": "gmail_price", "value": str(new_price)}).execute()
            flash("জিমেইলের অফিশিয়াল ক্রয়মূল্য সফলভাবে আপডেট করা হয়েছে।", "success")
            return redirect(url_for('admin_gmails'))
            
    # লাইভ জিমেইল প্রাইস এবং পেন্ডিং জিমেইলসমূহ রিট্রিভ করা
    price_res = supabase.table("settings").select("value").eq("key", "gmail_price").execute().data
    gmail_price = float(price_res[0]['value']) if price_res else 15.00
    
    pending_list = supabase.table("gmail_submissions") \
        .select("*, users:user_id(username, email, uid)") \
        .eq("status", "Pending") \
        .order("created_at", desc=True).execute().data or []
        
    return render_template('admin_gmails.html', pending_gmails=pending_list, gmail_price=gmail_price)


# ৩. এডমিন জিমেইল এপ্রুভ/রিজেক্ট অ্যাকশন রাউট (/admin/gmail-action)
@app.route('/admin/gmail-action', methods=['POST'])
def admin_gmail_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    submission_id = request.form.get('submission_id')
    action = request.form.get('action') # 'approve' or 'reject'
    
    sub_query = supabase.table("gmail_submissions").select("*").eq("id", submission_id).execute().data
    if not sub_query:
        flash("রেকর্ড খুঁজে পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_gmails'))
        
    sub = sub_query[0]
    target_user_id = sub['user_id']
    price = float(sub['price'])
    sub_email = sub['email']
    
    if action == 'approve':
        # স্ট্যাটাস Approved করা
        supabase.table("gmail_submissions").update({"status": "Approved"}).eq("id", submission_id).execute()
        # ইউজারের মূল ব্যালেন্সে টাকা যোগ করা
        supabase.rpc("increment_balance", {"user_id": target_user_id, "amount": price}).execute()
        
        # লেনদেন হিস্ট্রি বা লগ সেভ করা
        supabase.table("transactions").insert({
            "user_id": target_user_id,
            "title": f"Gmail Account Sold: {sub_email}",
            "amount": price
        }).execute()
        
        flash("জিমেইল অ্যাকাউন্টটি সফলভাবে এপ্রুভ এবং রিওয়ার্ড যোগ করা হয়েছে।", "success")
    elif action == 'reject':
        supabase.table("gmail_submissions").update({"status": "Rejected"}).eq("id", submission_id).execute()
        flash("জিমেইল অ্যাকাউন্টটি রিজেক্ট করা হয়েছে।", "success")
        
    return redirect(url_for('admin_gmails'))

# (অন্যান্য রাউটের সাথে নিচের নতুন রাউটটি যুক্ত করুন)

@app.route('/tutorial')
def tutorial_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    return render_template('tutorial.html', user=user)
    
@app.route('/fasset')
def fasset_landing():
    user_id = session.get('user_id')
    user = None
    if user_id:
        try:
            user_data = supabase.table("users").select("username", "uid", "avatar_url").eq("id", user_id).execute().data
            if user_data:
                user = user_data[0]
        except Exception:
            pass
    return render_template('fasset.html', user=user)

# (অন্যান্য এডমিন রাউটের সাথে নিচের নতুন রাউটটি যুক্ত করুন)

@app.route('/admin/task-bulk-action', methods=['POST'])
def admin_task_bulk_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    # ১. প্রথম ২০টি পেন্ডিং সাবমিশন রিট্রিভ করা
    pending_subs = supabase.table("task_submissions") \
        .select("id, user_id, tasks(title, reward)") \
        .eq("status", "Pending") \
        .limit(20).execute().data or []
        
    if not pending_subs:
        flash("বর্তমানে কোনো পেন্ডিং টাস্ক সাবমিশন নেই।", "danger")
        return redirect(url_for('admin_add_task'))
        
    total_count = len(pending_subs)
    
    # ২. র্যান্ডম রিজেকশন সংখ্যা নির্ধারণ (২/৩টি রিজেক্ট করার সুনির্দিষ্ট লজিক)
    if total_count >= 10:
        reject_count = random.randint(2, 3) # ১০ বা তার বেশি হলে ২/৩টি রিজেক্ট হবে
    elif total_count >= 3:
        reject_count = 1                   # ৩টির বেশি হলে ১টি রিজেক্ট হবে
    else:
        reject_count = 0                   # ৩টির নিচে হলে সব এপ্রুভ হবে
        
    # র্যান্ডমলি কোন কোন ইনডেক্স রিজেক্ট হবে তা সিলেক্ট করা হচ্ছে
    reject_indices = set(random.sample(range(total_count), reject_count))
    
    approved_count = 0
    rejected_count = 0
    
    # ৩. বাল্ক লুপিং প্রসেস
    for index, sub in enumerate(pending_subs):
        submission_id = sub['id']
        target_user_id = sub['user_id']
        reward = float(sub['tasks']['reward']) if sub.get('tasks') else 0.00
        task_title = sub['tasks']['title'] if sub.get('tasks') else "Task"
        
        if index in reject_indices:
            # রিজেক্ট করা হচ্ছে
            supabase.table("task_submissions").update({"status": "Rejected"}).eq("id", submission_id).execute()
            rejected_count += 1
        else:
            # এপ্রুভ করা হচ্ছে
            supabase.table("task_submissions").update({"status": "Approved"}).eq("id", submission_id).execute()
            # ব্যালেন্স অ্যাড করা হচ্ছে
            supabase.rpc("increment_balance", {"user_id": target_user_id, "amount": reward}).execute()
            
            # লেনদেন হিস্ট্রি লগ সেভ
            supabase.table("transactions").insert({
                "user_id": target_user_id,
                "title": f"Task Approved: {task_title}",
                "amount": reward
            }).execute()
            approved_count += 1
            
    flash(f"বাল্ক অটো-ভেরিফিকেশন সম্পন্ন! {approved_count}টি টাস্ক Approved এবং {rejected_count}টি টাস্ক Rejected করা হয়েছে।", "success")
    return redirect(url_for('admin_add_task'))
    
@app.route('/updates')
def updates_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    # select("*") দিয়ে ইউজারের সমস্ত প্রোফাইল ও ব্যালেন্স ডাটা নেওয়া হচ্ছে
    user_query = supabase.table("users").select("*").eq("id", user_id).execute().data
    if not user_query:
        session.clear()
        return redirect(url_for('login'))
        
    user = user_query[0]
    is_admin = user.get('is_admin', False)
    
    all_updates = supabase.table("updates").select("*").order("created_at", desc=True).execute().data or []
    
    return render_template('updates.html', user=user, updates=all_updates, is_admin=is_admin)
    

# ২. এডমিন কতৃক চ্যানেল আপডেট পোস্ট ডিলিট করার রাউট (/admin/delete-update)
@app.route('/admin/delete-update', methods=['POST'])
def admin_delete_update():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    update_id = request.form.get('update_id')
    if update_id:
        try:
            supabase.table("updates").delete().eq("id", update_id).execute()
            flash("আপডেট নোটিশটি সফলভাবে মুছে ফেলা হয়েছে।", "success")
        except Exception as e:
            print("Error deleting update:", e)
            flash("আপডেট নোটিশটি মুছতে ত্রুটি ঘটেছে।", "danger")
            
    return redirect(url_for('updates_page'))    

# ২. এডমিন কতৃক নতুন আপডেট নোটিশ যুক্ত করার রাউট
@app.route('/admin/add-update', methods=['POST'])
def admin_add_update():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    post_path = request.form.get('post_path').strip()
    
    # এডমিন যদি কেবল পোস্ট আইডি (যেমন: 49) টাইপ করে, তবে তা স্বয়ংক্রিয়ভাবে অরিজিনাল পাথে কনভার্ট হবে
    if post_path.isdigit():
        post_path = f"ortiwokr/{post_path}"
        
    try:
        supabase.table("updates").insert({"post_path": post_path}).execute()
        flash("নতুন চ্যানেল আপডেট সফলভাবে ড্যাশবোর্ডে পোস্ট করা হয়েছে।", "success")
    except Exception:
        flash("এই আপডেটটি ইতিমধ্যে পোস্ট করা রয়েছে।", "danger")
        
    return redirect(url_for('admin_add_task'))
    


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        phone = request.form.get('phone_number')
        age = request.form.get('age')
        district = request.form.get('district')
        proof_url = request.form.get('avatar_url')
        username = request.form.get('username')
        
        update_data = {}
        if username: update_data['username'] = username
        if phone: update_data['phone_number'] = phone
        if age: update_data['age'] = int(age) if age.isdigit() else None
        if district: update_data['district'] = district
        if proof_url: update_data['avatar_url'] = proof_url
        
        if update_data:
            supabase.table("users").update(update_data).eq("id", user_id).execute()
            flash("প্রোফাইল তথ্য সফলভাবে আপডেট করা হয়েছে।", "success")
            return redirect(url_for('profile'))
            
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    ref_link = request.url_root + "register?ref=" + str(user['uid'])
    
    return render_template('profile.html', user=user, ref_link=ref_link)
    
@app.route('/about')
def about():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    return render_template('about.html', user=user)
    

@app.route('/referrals')
def referrals():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    # select("*") দিয়ে ইউজারের সমস্ত প্রোফাইল ও ব্যালেন্স ডাটা নেওয়া হচ্ছে
    user_query = supabase.table("users").select("*").eq("id", user_id).execute().data
    if not user_query:
        session.clear()
        return redirect(url_for('login'))
    user = user_query[0]
    
    # সরাসরি ডাটাবেজ থেকে রিয়েল-টাইম রেফারেল তথ্য সংগ্রহ করা হচ্ছে
    referrals_data = supabase.table("referrals") \
        .select("status, created_at, users:referred_id(username, email)") \
        .eq("referrer_id", user_id).execute().data or []
        
    success_count = sum(1 for r in referrals_data if r['status'] == 'Success')
    processing_count = sum(1 for r in referrals_data if r['status'] == 'Processing')
    failed_count = sum(1 for r in referrals_data if r['status'] == 'Failed')
    total_earnings = success_count * 15.00
        
    ref_link = request.url_root + "register?ref=" + str(user['uid'])
    
    # user=user নিশ্চিতভাবে টেমপ্লেটে পাঠানো হলো
    return render_template('referrals.html', 
                           user=user,
                           referrals=referrals_data, 
                           ref_link=ref_link,
                           success_count=success_count,
                           processing_count=processing_count,
                           failed_count=failed_count,
                           total_earnings=total_earnings)
    
@app.route('/admin/task', methods=['GET'])
def admin_task_hub():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    # শুধুমাত্র একটিভ নরমাল কাজের তালিকা কোয়েরি করা হচ্ছে
    all_tasks = supabase.table("tasks").select("*").order("created_at", desc=True).execute().data or []
    return render_template('admin_task_hub.html', tasks=all_tasks)
    
# ২. নতুন টাস্ক তৈরি করার রাউট
@app.route('/admin/task/create', methods=['POST'])
def admin_create_task():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    title = request.form.get('title')
    description = request.form.get('description')
    link = request.form.get('link')
    reward = float(request.form.get('reward', 0))
    
    supabase.table("tasks").insert({
        "title": title,
        "description": description,
        "link": link,
        "reward": reward
    }).execute()
    
    flash("নতুন নরমাল টাস্কটি সফলভাবে যুক্ত হয়েছে।", "success")
    return redirect(url_for('admin_task_hub'))

# (অন্যান্য কোডের সাথে নিচের নতুন অপটিবুস্ট ইউজার এবং এডমিন ভেরিফিকেশন রাউটগুলো যুক্ত করুন)

# ১. ইউজার অপটিবুস্ট পেজ রাউট (/optiboost)
@app.route('/optiboost', methods=['GET', 'POST'])
def optiboost_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    # ইউজারের পূর্ববর্তী কোনো অপটিবুস্ট রিকোয়েস্ট আছে কিনা তা চেক
    boost_query = supabase.table("optiboost_requests").select("status").eq("user_id", user_id).execute().data
    boost_status = boost_query[0]['status'] if boost_query else None
    
    if request.method == 'POST':
        method = request.form.get('method')
        number = request.form.get('number')
        tx_id = request.form.get('transaction_id')
        
        if boost_status == 'Pending' or boost_status == 'Approved':
            flash("আপনার একটি রিকোয়েস্ট ইতিমধ্যে প্রক্রিয়াধীন অথবা অনুমোদিত রয়েছে।", "danger")
            return redirect(url_for('optiboost_page'))
            
        try:
            supabase.table("optiboost_requests").insert({
                "user_id": user_id,
                "payment_method": method,
                "payment_number": number,
                "transaction_id": tx_id.strip(),
                "status": "Pending"
            }).execute()
            flash("আপনার অপটিবুস্ট রিকোয়েস্ট সফলভাবে জমা হয়েছে। এডমিন ভেরিফাই করবে।", "success")
            return redirect(url_for('optiboost_page'))
        except Exception:
            flash("এই ট্রানজেকশন আইডিটি ইতিমধ্যে ব্যবহৃত হয়েছে।", "danger")
            
    return render_template('optiboost.html', user=user, boost_status=boost_status)


# ২. এডমিন অপটিবুস্ট ভেরিফিকেশন প্যানেল (/admin/opti)
@app.route('/admin/opti')
def admin_opti():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    pending = supabase.table("optiboost_requests") \
        .select("id, payment_method, payment_number, transaction_id, status, created_at, users(username, email, uid)") \
        .eq("status", "Pending") \
        .order("created_at", desc=True).execute().data or []
        
    return render_template('admin_opti.html', pending_boosts=pending)


# ৩. এডমিন অপটিবুস্ট এপ্রুভ/রিজেক্ট অ্যাকশন রাউট
@app.route('/admin/opti/action', methods=['POST'])
def admin_opti_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    request_id = request.form.get('request_id')
    action = request.form.get('action') # 'approve' or 'reject'
    
    boost_req = supabase.table("optiboost_requests").select("user_id").eq("id", request_id).execute().data
    if not boost_req:
        flash("রেকর্ড খুঁজে পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_opti'))
        
    target_user_id = boost_req[0]['user_id']
    
    if action == 'approve':
        # অপটিবুস্ট রিকোয়েস্ট এপ্রুভ করা
        supabase.table("optiboost_requests").update({"status": "Approved"}).eq("id", request_id).execute()
        # ইউজারের প্রফাইল কার্ডে OptiBoost সক্রিয় (TRUE) করা
        supabase.table("users").update({"is_optiboost": True}).eq("id", target_user_id).execute()
        flash("অপটিবুস্ট রিকোয়েস্ট সফলভাবে অনুমোদিত (Approved) হয়েছে।", "success")
    elif action == 'reject':
        supabase.table("optiboost_requests").update({"status": "Rejected"}).eq("id", request_id).execute()
        flash("অপটিবুস্ট রিকোয়েস্ট বাতিল (Rejected) করা হয়েছে।", "success")
        
    return redirect(url_for('admin_opti'))
            
# ৩. টাস্ক এডিট করার রাউট (আলাদা এডিট পেজ)
@app.route('/admin/task/edit/<task_id>', methods=['GET', 'POST'])
def admin_edit_task(task_id):
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        link = request.form.get('link')
        reward = float(request.form.get('reward', 0))
        
        supabase.table("tasks").update({
            "title": title,
            "description": description,
            "link": link,
            "reward": reward
        }).eq("id", task_id).execute()
        
        flash("টাস্ক তথ্য সফলভাবে আপডেট করা হয়েছে।", "success")
        return redirect(url_for('admin_task_hub'))
        
    task_query = supabase.table("tasks").select("*").eq("id", task_id).execute().data
    if not task_query:
        flash("টাস্কটি খুঁজে পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_task_hub'))
        
    return render_template('admin_task_edit.html', task=task_query[0])


# ৪. অ্যাক্টিভ টাস্ক ডিলিট করার রাউট
@app.route('/admin/task/delete', methods=['POST'])
def admin_delete_task():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    task_id = request.form.get('task_id')
    supabase.table("tasks").delete().eq("id", task_id).execute()
    
    flash("টাস্কটি ডাটাবেজ থেকে মুছে ফেলা হয়েছে।", "success")
    return redirect(url_for('admin_task_hub'))
    
    
# app.py ফাইলের /admin/withdrawals রাউটটি এটি দিয়ে প্রতিস্থাপন করুন
@app.route('/admin/withdrawals')
def admin_withdrawals():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    pending = supabase.table("withdrawals") \
        .select("*, users:user_id(username, email, uid)") \
        .eq("status", "Pending") \
        .order("created_at", desc=True).execute().data or []
        
    # প্রতিটি পেন্ডিং রিকোয়েস্টের বিপরীতে ওই ইউজারের পূর্ববর্তী 'Rejected' সংখ্যা রিয়েল-টাইমে বের করা
    for item in pending:
        target_user_id = item['user_id']
        reject_query = supabase.table("withdrawals") \
            .select("id", count="exact") \
            .eq("user_id", target_user_id) \
            .eq("status", "Rejected").execute()
            
        reject_count = reject_query.count if reject_query.count is not None else 0
        item['reject_count'] = reject_count # রিয়েল-টাইম কাউন্ট অ্যাপেন্ড করা হলো
        
    return render_template('admin_withdraw.html', pending_withdrawals=pending)
    

# ২. উইথড্র এপ্রুভ/রিজেক্ট অ্যাকশন এবং অটোমেটিক টেলিগ্রাম নোটিফিকেশন ট্রিগার
@app.route('/admin/withdraw-action', methods=['POST'])
def admin_withdraw_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    withdraw_id = request.form.get('withdraw_id')
    action = request.form.get('action') # 'approve' অথবা 'reject'
    
    # উইথড্রয়াল তথ্য ও রেফার করা ইউজারের UID সংগ্রহ করা
    withdraw_query = supabase.table("withdrawals") \
        .select("*, users:user_id(uid)") \
        .eq("id", withdraw_id).execute().data
        
    if not withdraw_query:
        flash("উইথড্র রেকর্ড পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_withdrawals'))
        
    w = withdraw_query[0]
    user_id = w['user_id']
    amount = float(w['amount'])
    uid = w['users']['uid']
    method = w['payment_method']
    number = w['payment_number']
    is_agent = w.get('is_agent_withdrawal', False)
    
    if action == 'approve':
        # ১. ডাটাবেজে স্ট্যাটাস Approved করা
        supabase.table("withdrawals").update({"status": "Approved"}).eq("id", withdraw_id).execute()
        
        # ২. টেলিগ্রাম চ্যানেলে ইনলাইন বাটন সহ SUCCESS নোটিফিকেশন পাঠানো
        masked_number = number[:3] + "*****" + number[-3:]
        success_msg = f"""<b>✅ WITHDRAWAL SUCCESSFUL</b>
────────────────────
<b>User UID:</b> <code>#{uid}</code>
<b>Amount:</b> ৳ {amount}
<b>Gateway:</b> {method}
<b>Number:</b> {masked_number}
<b>Status:</b> 🟢 Completed (Success)
────────────────────
<i>Payout processed via Automated Node!</i>"""
        send_telegram_notification(success_msg)
        
        flash("উইথড্র রিকোয়েস্ট সফলভাবে এপ্রুভ এবং টেলিগ্রামে পোস্ট করা হয়েছে।", "success")
        
    elif action == 'reject':
        # ১. ডাটাবেজে স্ট্যাটাস Rejected করা
        supabase.table("withdrawals").update({"status": "Rejected"}).eq("id", withdraw_id).execute()
        
        # ২. টাকা রিফান্ড করা (এজেন্ট উইথড্র হলে এজেন্ট ব্যালেন্সে, সাধারণ উইথড্র হলে মূল ব্যালেন্সে)
        if is_agent:
            supabase.rpc("increment_agent_balance", {"user_id": user_id, "amount": amount}).execute()
        else:
            supabase.rpc("increment_balance", {"user_id": user_id, "amount": amount}).execute()
            
        flash("উইথড্র রিকোয়েস্ট রিজেক্ট করা হয়েছে এবং ব্যালেন্স সফলভাবে রিফান্ড হয়েছে।", "success")
        
    return redirect(url_for('admin_withdrawals'))
    

@app.route('/api/upload', methods=['POST'])
def api_upload_image():
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No image file provided."}), 400
        
    file = request.files['image']
    file_bytes = file.read()
    base64_image = base64.b64encode(file_bytes)
    
    while True:
        # ধাপ ক: প্রথমে সক্রিয় ImgBB কী খুঁজবে
        imgbb_query = supabase.table("imgbb_keys") \
            .select("id, key_value") \
            .eq("status", "Active") \
            .order("created_at", desc=False) \
            .limit(1).execute().data
            
        if imgbb_query:
            key_id = imgbb_query[0]['id']
            key_value = imgbb_query[0]['key_value']
            
            try:
                payload = urllib.parse.urlencode({"image": base64_image}).encode("utf-8")
                url = f"https://api.imgbb.com/1/upload?key={key_value}"
                req = urllib.request.Request(url, data=payload)
                
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    
                if res_data.get('success'):
                    return jsonify({"status": "success", "url": res_data['data']['url']}), 200
                else:
                    raise Exception("ImgBB reject")
            except Exception:
                # ImgBB কি ব্লক বা ফেইল হলে Failed মার্ক করে লুপটি পুনরায় চালু করবে পরবর্তী কি নেওয়ার জন্য
                supabase.table("imgbb_keys").update({"status": "Failed"}).eq("id", key_id).execute()
                continue
                
        # ধাপ খ: যদি কোনো সক্রিয় ImgBB কি না থাকে, তবে স্বয়ংক্রিয়ভাবে Freeimage.host কি খুঁজবে
        freehost_query = supabase.table("freehost_keys") \
            .select("id, key_value") \
            .eq("status", "Active") \
            .order("created_at", desc=False) \
            .limit(1).execute().data
            
        if freehost_query:
            key_id = freehost_query[0]['id']
            key_value = freehost_query[0]['key_value']
            
            try:
                # Freeimage.host (Chevereto Engine) এপিআই রিকোয়েস্ট পেলোড
                payload = urllib.parse.urlencode({
                    "key": key_value,
                    "action": "upload",
                    "source": base64_image,
                    "format": "json"
                }).encode("utf-8")
                
                url = "https://freeimage.host/api/1/upload"
                req = urllib.request.Request(url, data=payload)
                
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    
                if res_data.get('status_code') == 200 and 'image' in res_data:
                    return jsonify({"status": "success", "url": res_data['image']['url']}), 200
                else:
                    raise Exception("Freehost reject")
            except Exception:
                # Freeimage.host কি ফেইল হলে Failed মার্ক করে লুপটি পুনরায় চালু করবে
                supabase.table("freehost_keys").update({"status": "Failed"}).eq("id", key_id).execute()
                continue
                
        # ধাপ গ: যদি দুটি হোস্টের কোনো সক্রিয় কি-ই অবশিষ্ঠ না থাকে
        return jsonify({"status": "error", "message": "কোনো ইমেজ হোস্টিং সার্ভিস সক্রিয় নেই। অনুগ্রহ করে এডমিনের সাথে যোগাযোগ করুন।"}), 500
        

# ২. এডমিন এপিআই কি ম্যানেজার রাউট (বিকল্প গেটওয়ে সিলেক্টর সহ)
@app.route('/admin/keys', methods=['GET', 'POST'])
def admin_keys():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    if request.method == 'POST':
        new_key = request.form.get('key_value')
        host_type = request.form.get('host_type') # 'imgbb' অথবা 'freehost'
        
        if new_key and host_type:
            table_name = "imgbb_keys" if host_type == 'imgbb' else "freehost_keys"
            try:
                supabase.table(table_name).insert({"key_value": new_key.strip(), "status": "Active"}).execute()
                flash("নতুন এপিআই কী সফলভাবে সচল তালিকায় যুক্ত করা হয়েছে।", "success")
            except Exception:
                flash("এই এপিআই কী-টি ইতিমধ্যে ডাটাবেজে সংরক্ষিত রয়েছে।", "danger")
        return redirect(url_for('admin_keys'))
        
    imgbb_list = supabase.table("imgbb_keys").select("*").order("created_at", desc=True).execute().data or []
    freehost_list = supabase.table("freehost_keys").select("*").order("created_at", desc=True).execute().data or []
    
    return render_template('admin_keys.html', imgbb_keys=imgbb_list, freehost_keys=freehost_list)



# ৩. এডমিন এপিআই কি ডিলিট রাউট (ডাইনামিক টেবিল রিমুভার সহ)
@app.route('/admin/keys/delete', methods=['POST'])
def admin_delete_key():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    key_id = request.form.get('key_id')
    host_type = request.form.get('host_type') # 'imgbb' অথবা 'freehost'
    
    table_name = "imgbb_keys" if host_type == 'imgbb' else "freehost_keys"
    supabase.table(table_name).delete().eq("id", key_id).execute()
    
    flash("এপিআই কী-টি সফলভাবে ডাটাবেজ থেকে মুছে ফেলা হয়েছে।", "success")
    return redirect(url_for('admin_keys'))
    
@app.route('/agent')
def agent_portal():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    if not user.get('is_agent'):
        return "Access Denied (403)", 403
        
    referred_users = supabase.table("referrals") \
        .select("status, created_at, users:referred_id(id, uid, username, email, balance)") \
        .eq("referrer_id", user_id).execute().data
        
    referred_ids = [r['users']['id'] for r in referred_users if r.get('users')]
    
    deposits_list = []
    if referred_ids:
        deposits_list = supabase.table("deposits") \
            .select("amount, status, created_at, users(username, uid)") \
            .in_("user_id", referred_ids) \
            .eq("status", "Approved") \
            .order("created_at", desc=True).execute().data

    withdraw_history = supabase.table("withdrawals") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("is_agent_withdrawal", True) \
        .order("created_at", desc=True).execute().data

    return render_template('agent.html', 
                           user=user, 
                           referred_users=referred_users, 
                           deposits=deposits_list,
                           withdraw_history=withdraw_history)


@app.route('/agent/withdraw', methods=['POST'])
def agent_withdraw():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("is_agent, agent_balance").eq("id", user_id).execute().data[0]
    if not user.get('is_agent'):
        return "Unauthorized Action", 403
        
    agent_balance = float(user['agent_balance'])
    amount = float(request.form.get('amount'))
    method = request.form.get('method')
    number = request.form.get('number')
    
    if amount < 50.00:
        flash("এজেন্ট উইথড্রয়াল ন্যূনতম ৫০ টাকা হতে হবে।", "danger")
    elif amount > agent_balance:
        flash("আপনার এজেন্ট ব্যালেন্স অপর্যাপ্ত।", "danger")
    else:
        supabase.rpc("increment_agent_balance", {"user_id": user_id, "amount": -amount}).execute()
        
        supabase.table("withdrawals").insert({
            "user_id": user_id,
            "amount": amount,
            "payment_method": method,
            "payment_number": number,
            "status": "Pending",
            "is_agent_withdrawal": True
        }).execute()
        
        flash("এজেন্ট উইথড্রয়াল অনুরোধ সফলভাবে জমা হয়েছে।", "success")
        
    return redirect(url_for('agent_portal'))



@app.route('/admin/deposits')
def admin_deposits():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    # পেন্ডিং থাকা ডিপোজিটসমূহ এবং ইউজারের ইউনিক তথ্য সংগ্রহ (Postgrest standard join)
    pending = supabase.table("deposits") \
        .select("*, users:user_id(username, email, uid)") \
        .eq("status", "Pending") \
        .order("created_at", desc=True).execute().data or []
        
    return render_template('admin_deposit.html', pending_deposits=pending)

@app.route('/admin/deposit-action', methods=['POST'])
def admin_deposit_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    deposit_id = request.form.get('deposit_id')
    action = request.form.get('action') # 'approve' অথবা 'reject'
    
    dep_query = supabase.table("deposits").select("*").eq("id", deposit_id).execute().data
    if not dep_query:
        flash("ডিপোজিট রেকর্ড পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_deposits'))
        
    dep = dep_query[0]
    target_user_id = dep['user_id']
    amount = float(dep['amount'])
    
    if action == 'approve':
        # ১. ডাটাবেজে ডিপোজিট স্ট্যাটাস 'Approved' করা
        supabase.table("deposits").update({"status": "Approved"}).eq("id", deposit_id).execute()
        
        # ২. ইউজারের মূল ব্যালেন্সে টাকা যোগ করা
        supabase.rpc("increment_balance", {"user_id": target_user_id, "amount": amount}).execute()
        
        # ৩. আপলাইন এজেন্ট চেক করে ৫০% কমিশন প্রদান করা
        ref_query = supabase.table("referrals").select("referrer_id").eq("referred_id", target_user_id).execute().data
        if ref_query:
            referrer_id = ref_query[0]['referrer_id']
            referrer_user = supabase.table("users").select("is_agent").eq("id", referrer_id).execute().data
            if referrer_user and referrer_user[0]['is_agent']:
                commission = amount * 0.50
                supabase.rpc("increment_agent_balance", {"user_id": referrer_id, "amount": commission}).execute()
                
        flash("ডিপোজিট এপ্রুভ এবং ব্যালেন্স সফলভাবে যোগ করা হয়েছে।", "success")
    elif action == 'reject':
        # ডিপোজিট বাতিল করা
        supabase.table("deposits").update({"status": "Rejected"}).eq("id", deposit_id).execute()
        flash("ডিপোজিট রিকোয়েস্ট রিজেক্ট করা হয়েছে।", "success")
        
    # অ্যাকশন শেষ হওয়ার পর পুনরায় ডিপোজিট লিস্ট পেজে রিডাইরেক্ট করা
    return redirect(url_for('admin_deposits'))
    
# ১. টাস্ক তালিকা রাউট (/tasks)
@app.route('/tasks')
@require_activation
def tasks():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user_res = supabase.table("users").select("*").eq("id", user_id).execute().data
    if not user_res:
        session.clear()
        return redirect(url_for('login'))
    user = user_res[0]
    
    # ইউজার ইতিমধ্যে ক্লেইম করা ওয়ান-টাইম টাস্কগুলোর তালিকা
    completed_one_times = supabase.table("user_one_time_tasks") \
        .select("task_name").eq("user_id", user_id).execute().data or []
    claimed_one_times = [t['task_name'] for t in completed_one_times]
    
    # সফল রেফারেল সংখ্যা যাচাই
    success_refs_query = supabase.table("referrals").select("id").eq("referrer_id", user_id).eq("status", "Success").execute().data or []
    success_ref_count = len(success_refs_query)
    
    # প্রোফাইল সম্পূর্ণ করা হয়েছে কিনা যাচাই করা
    is_profile_complete = bool(user.get('phone_number') and user.get('age') and user.get('district'))
    
    # ইউজারের সাবমিট করা পূর্ববর্তী নরমাল টাস্কের ডাটা
    submissions = supabase.table("task_submissions").select("task_id, status").eq("user_id", user_id).execute().data or []
    submission_map = {s['task_id']: s['status'] for s in submissions}
    
    # এডমিনের তৈরি সমস্ত নরমাল টাস্কসমূহ
    all_normal_tasks = supabase.table("tasks").select("*").order("created_at", desc=True).execute().data or []
    
    # ফিল্টারিং লজিক: কেবল সেই কাজগুলোই দেখাবে যা ইউজার সাবমিট করেনি অথবা পূর্বে 'Rejected' হয়েছে
    active_normal_tasks = []
    for task in all_normal_tasks:
        status = submission_map.get(task['id'])
        if status is None or status == 'Rejected':
            active_normal_tasks.append(task)

    # user=user নিশ্চিতভাবে পাস করা হলো
    return render_template('tasks.html', 
                           user=user,
                           claimed_one_times=claimed_one_times,
                           success_ref_count=success_ref_count,
                           is_profile_complete=is_profile_complete,
                           all_normal_tasks=active_normal_tasks,
                           submission_map=submission_map)


# ২. ডেডিকেটেড টাস্ক ডিটেইলস ও স্টেপ-বাই-স্টেপ সাবমিশন রাউট (/tasks/<task_id>)
@app.route('/tasks/<task_id>')
def task_detail(task_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user_res = supabase.table("users").select("*").eq("id", user_id).execute().data
    if not user_res:
        session.clear()
        return redirect(url_for('login'))
    user = user_res[0]
    
    # নির্দিষ্ট টাস্ক আইডি দিয়ে ডাটা কুয়েরি
    task_query = supabase.table("tasks").select("*").eq("id", task_id).execute().data
    if not task_query:
        flash("টাস্কটি খুঁজে পাওয়া যায়নি।", "danger")
        return redirect(url_for('tasks'))
        
    task = task_query[0]
    
    # এই কাজের জন্য পূর্বে কোনো সাবমিশন করা হয়েছে কিনা চেক করা
    submission_query = supabase.table("task_submissions") \
        .select("status, proof_image_url") \
        .eq("user_id", user_id).eq("task_id", task_id).execute().data
        
    status = submission_query[0]['status'] if submission_query else None
    proof_url = submission_query[0]['proof_image_url'] if submission_query else None
    
    # user=user নিশ্চিতভাবে পাস করা হলো
    return render_template('task_detail.html', user=user, task=task, status=status, proof_url=proof_url)
    
# app.py ফাইলের /tasks/submit-normal রাউটটি এটি দিয়ে পরিবর্তন করুন
@app.route('/tasks/submit-normal', methods=['POST'])
def submit_normal():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    task_id = request.form.get('task_id')
    proof_url = request.form.get('proof_image_url')
    
    # কাজের প্রুফ না থাকলে হোম পেজের বদলে সরাসরি সেই টাস্কের ডিটেইলস পেজেই রিডাইরেক্ট করবে
    if not proof_url:
        flash("দয়া করে কাজের প্রুফ (স্ক্রিনশট) আপলোড করুন।", "danger")
        return redirect(url_for('task_detail', task_id=task_id))
        
    try:
        # Rejected থাকা পূর্ববর্তী ডাটা ডিলিট করে দেওয়া হচ্ছে
        supabase.table("task_submissions").delete() \
            .eq("user_id", user_id).eq("task_id", task_id).eq("status", "Rejected").execute()
        
        # নতুন পেন্ডিং রিকোয়েস্ট ইনসার্ট
        supabase.table("task_submissions").insert({
            "user_id": user_id,
            "task_id": task_id,
            "proof_image_url": proof_url,
            "status": "Pending"
        }).execute()
        flash("কাজের প্রুফ সফলভাবে জমা দেওয়া হয়েছে। এডমিন ভেরিফাই করবে।", "success")
    except Exception:
        flash("এই কাজটি ইতিমধ্যে প্রক্রিয়াধীন (Pending) অথবা অনুমোদিত (Approved) আছে।", "danger")
        
    return redirect(url_for('tasks'))

@app.route('/history')
def history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    # ১. ইউজার ডাটা ফেচ (সেইফ রিট্রাই)
    user = None
    for _ in range(2):
        try:
            u_res = supabase.table("users").select("*").eq("id", user_id).execute().data
            if u_res:
                user = u_res[0]
                break
        except Exception as e:
            print("History User Fetch Retry:", e)
            
    if not user:
        session.clear()
        return redirect(url_for('login'))
        
    # ২. ডিপোজিট হিস্ট্রি
    deposits = []
    try:
        dep_res = supabase.table("deposits").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        deposits = dep_res.data or []
    except Exception as e:
        print("History Deposits Error:", e)
        deposits = []

    # ৩. উইথড্রয়াল হিস্ট্রি
    withdrawals = []
    try:
        with_res = supabase.table("withdrawals").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        withdrawals = with_res.data or []
    except Exception as e:
        print("History Withdrawals Error:", e)
        withdrawals = []

    # ৪. টাস্ক সাবমিশন হিস্ট্রি
    task_history = []
    try:
        t_res = supabase.table("task_submissions") \
            .select("proof_image_url, status, created_at, tasks:task_id(title, reward)") \
            .eq("user_id", user_id).order("created_at", desc=True).execute()
        task_history = t_res.data or []
    except Exception as e:
        print("History Task History Error:", e)
        task_history = []

    # ৫. ট্রানজেকশন হিস্ট্রি
    transactions = []
    try:
        tx_res = supabase.table("transactions") \
            .select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        transactions = tx_res.data or []
    except Exception as e:
        print("History Transactions Error:", e)
        transactions = []

    # ৬. নিরাপদ ডেট ও ইনকাম হিসাব
    now = datetime.datetime.now(datetime.timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - datetime.timedelta(days=1)
    yesterday_end = today_start

    today_income = 0.00
    yesterday_income = 0.00
    total_income = 0.00

    for tx in transactions:
        try:
            amount = float(tx.get('amount', 0))
            raw_date = str(tx.get('created_at', ''))
            
            if amount > 0 and raw_date:
                total_income += amount
                tx_date = datetime.datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                
                if tx_date >= today_start:
                    today_income += amount
                elif yesterday_start <= tx_date < yesterday_end:
                    yesterday_income += amount
        except Exception:
            pass

    return render_template('history.html', 
                           user=user,
                           transactions=transactions, 
                           withdrawals=withdrawals, 
                           task_history=task_history,
                           today_income=round(today_income, 2),
                           yesterday_income=round(yesterday_income, 2),
                           total_income=round(total_income, 2))
    
@app.route('/admin/user-action', methods=['POST'])
def admin_user_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    target_id = request.form.get('user_id')
    action = request.form.get('action')
    
    if action == 'ban':
        supabase.table("users").update({"is_banned": True}).eq("id", target_id).execute()
        flash("ইউজার অ্যাকাউন্ট সাময়িকভাবে স্থগিত (Banned) করা হয়েছে।", "success")
        
    elif action == 'unban':
        supabase.table("users").update({"is_banned": False}).eq("id", target_id).execute()
        flash("ইউজার অ্যাকাউন্ট পুনরায় সক্রিয় (Unbanned) করা হয়েছে।", "success")
        
    elif action == 'delete':
        supabase.table("users").delete().eq("id", target_id).execute()
        flash("ইউজার ডাটাবেজ থেকে সম্পূর্ণ মুছে ফেলা হয়েছে।", "success")
        
    elif action == 'add_balance':
        amount = float(request.form.get('amount', 0))
        supabase.rpc("increment_balance", {"user_id": target_id, "amount": amount}).execute()
        flash(f"সফলভাবে {amount} টাকা যোগ করা হয়েছে।", "success")
        
    elif action == 'add_referral':
        supabase.table("referrals").insert({
            "referrer_id": target_id,
            "status": "Success",
            "scheduled_payout_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }).execute()
        
        supabase.rpc("increment_balance", {"user_id": target_id, "amount": 30.00}).execute()
        flash("ম্যানুয়ালি ১টি সফল রেফারেল এবং ৩০ টাকা যোগ করা হয়েছে।", "success")
        
    return redirect(url_for('admin_dashboard'))


# (অন্যান্য এডমিন রাউটের সাথে নিচের নতুন রাউটটি যুক্ত করুন)
@app.route('/admin/user-search')
def admin_user_search():
    if not check_admin_auth():
        flash("Unauthorized Access", "danger")
        return redirect(url_for('login'))
        
    query = request.args.get('query', '').strip()
    target_user = None
    task_history = []
    withdraw_history = []
    referrals_history = []
    ad_share_history = []
    gmail_history = []
    
    if query:
        try:
            # ১. ইউআইডি (UID) অথবা ইমেইল দিয়ে সার্চ করা হচ্ছে
            if query.isdigit():
                u_query = supabase.table("users").select("*").eq("uid", int(query)).execute().data
            else:
                u_query = supabase.table("users").select("*").ilike("email", f"%{query}%").execute().data
                
            if u_query:
                target_user = u_query[0]
                target_id = target_user['id']
                
                # ক. টাস্ক সাবমিশন হিস্ট্রি
                try:
                    task_history = supabase.table("task_submissions") \
                        .select("id, status, proof_image_url, created_at, tasks(title, reward)") \
                        .eq("user_id", target_id).order("created_at", desc=True).execute().data or []
                except Exception:
                    task_history = []
                    
                # খ. উইথড্রয়াল হিস্ট্রি
                try:
                    withdraw_history = supabase.table("withdrawals") \
                        .select("*") \
                        .eq("user_id", target_id).order("created_at", desc=True).execute().data or []
                except Exception:
                    withdraw_history = []
                    
                # গ. রেফারেল হিস্ট্রি
                try:
                    referrals_history = supabase.table("referrals") \
                        .select("status, created_at, users:referred_id(username, email, uid, balance)") \
                        .eq("referrer_id", target_id).order("created_at", desc=True).execute().data or []
                except Exception:
                    referrals_history = []

                # ঘ. ফেসবুক অ্যাড শেয়ার হিস্ট্রি
                try:
                    raw_ads = supabase.table("adshear_submissions") \
                        .select("*").eq("user_id", target_id).order("created_at", desc=True).execute().data or []
                    for ad in raw_ads:
                        t_res = supabase.table("adshear_tasks").select("title, reward").eq("id", ad['task_id']).execute().data
                        ad['adshear_tasks'] = t_res[0] if t_res else {'title': 'Ad Task', 'reward': 0}
                        ad_share_history.append(ad)
                except Exception:
                    ad_share_history = []

                # ঙ. জিমেইল সাবমিশন হিস্ট্রি
                try:
                    gmail_history = supabase.table("gmail_submissions") \
                        .select("*").eq("user_id", target_id).order("created_at", desc=True).execute().data or []
                except Exception:
                    gmail_history = []

        except Exception as e:
            print("Admin User Audit Error:", e)
            
    return render_template('admin_user_audit.html',
                           target_user=target_user,
                           task_history=task_history,
                           withdraw_history=withdraw_history,
                           referrals_history=referrals_history,
                           ad_share_history=ad_share_history,
                           gmail_history=gmail_history,
                           query=query)
    
@app.route('/tasks/claim-one-time', methods=['POST'])
def claim_one_time():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    task_name = request.json.get('task_name')
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    exists = supabase.table("user_one_time_tasks").select("id").eq("user_id", user_id).eq("task_name", task_name).execute().data
    if exists:
        return jsonify({"status": "error", "message": "এই টাস্কটি ইতিমধ্যে ক্লেইম করা হয়েছে।"})
        
    reward = 0.00
    
    success_refs_query = supabase.table("referrals").select("id").eq("referrer_id", user_id).eq("status", "Success").execute().data
    success_ref_count = len(success_refs_query)
    
    if task_name == 'profile_update':
        if user.get('phone_number') and user.get('age') and user.get('district'):
            reward = 5.00
        else:
            return jsonify({"status": "error", "message": "আপনার প্রোফাইলের সব তথ্য এখনও পূর্ণ করা হয়নি।"})
            
    elif task_name == 'join_channel':
        reward = 5.00
        
    elif task_name == 'watch_tutorial':
        reward = 5.00
        
    elif task_name == 'refer_3':
        if success_ref_count >= 3:
            reward = 50.00
        else:
            return jsonify({"status": "error", "message": "আপনার এখনো ৩টি সফল রেফারেল সম্পন্ন হয়নি।"})
            
    elif task_name == 'refer_10':
        if success_ref_count >= 10:
            reward = 150.00
        else:
            return jsonify({"status": "error", "message": "আপনার এখনো ১০টি সফল রেফারেল সম্পন্ন হয়নি।"})
    else:
        return jsonify({"status": "error", "message": "অবৈধ টাস্ক রিকোয়েস্ট।"})
        
    supabase.rpc("increment_balance", {"user_id": user_id, "amount": reward}).execute()
    supabase.table("user_one_time_tasks").insert({"user_id": user_id, "task_name": task_name}).execute()
    
    supabase.table("transactions").insert({
        "user_id": user_id,
        "title": f"One-Time Task Completed: {task_name.replace('_', ' ').title()}",
        "amount": reward
    }).execute()
    
    return jsonify({"status": "success", "message": f"সফলভাবে ক্লেইমড! আপনার ব্যালেন্সে ৳ {reward} যোগ করা হয়েছে। "})


@app.route('/admin/add', methods=['GET', 'POST'])
def admin_add_task():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        link = request.form.get('link')
        reward = float(request.form.get('reward'))
        
        supabase.table("tasks").insert({
            "title": title,
            "description": description,
            "link": link,
            "reward": reward
        }).execute()
        flash("নতুন নরমাল টাস্কটি সফলভাবে ডাটাবেজে যুক্ত হয়েছে।", "success")
        return redirect(url_for('admin_add_task'))
        
    pending_submissions = supabase.table("task_submissions") \
        .select("id, proof_image_url, status, created_at, users(username, email), tasks(title, reward)") \
        .eq("status", "Pending").execute().data
        
    return render_template('admin_add.html', pending_submissions=pending_submissions)


@app.route('/admin/task-action', methods=['POST'])
def admin_task_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    submission_id = request.form.get('submission_id')
    action = request.form.get('action')
    
    submission = supabase.table("task_submissions").select("*, tasks(reward)").eq("id", submission_id).execute().data
    if not submission:
        flash("সাবমিশন ডাটা পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_add_task'))
        
    sub = submission[0]
    user_id = sub['user_id']
    reward = float(sub['tasks']['reward'])
    
    if action == 'approve':
        supabase.table("task_submissions").update({"status": "Approved"}).eq("id", submission_id).execute()
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": reward}).execute()
        flash("টাস্ক সাবমিশন এপ্রুভ এবং ইউজারকে রিওয়ার্ড দেওয়া হয়েছে।", "success")
    elif action == 'reject':
        supabase.table("task_submissions").update({"status": "Rejected"}).eq("id", submission_id).execute()
        flash("টাস্ক সাবমিশন বাতিল (Rejected) করা হয়েছে।", "success")
        
    return redirect(url_for('admin_add_task'))


@app.route('/')
def home():
    user_id = session.get('user_id')
    user = None
    if user_id:
        try:
            user_data = supabase.table("users").select("username", "uid").eq("id", user_id).execute().data
            if user_data:
                user = user_data[0]
        except Exception:
            pass
    return render_template('home.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_query = supabase.table("users").select("*").eq("email", email).execute()
        
        if user_query.data:
            user = user_query.data[0]
            
            if user.get('is_banned'):
                flash("আপনার অ্যাকাউন্টটি সাময়িকভাবে স্থগিত (Banned) করা হয়েছে।", "danger")
                return render_template('login.html')
                
            is_valid = False
            db_hash = user['password_hash']
            
            # ১. প্রথমে স্ট্যান্ডার্ড সিকিউর হ্যাশ চেক করার চেষ্টা করা হবে
            if db_hash.startswith(('pbkdf2:', 'scrypt:', 'sha256:', 'bcrypt:')):
                try:
                    is_valid = check_password_hash(db_hash, password)
                except Exception:
                    pass
            
            # ২. হ্যাশ ফেইল করলে বা সরাসরি সাধারণ টেক্সট (যেমন: 12345678) দেওয়া থাকলে তা চেক করবে
            if not is_valid:
                is_valid = (db_hash == password)
                
            if is_valid:
                session.permanent = True
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['uid'] = user['uid']
                
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                supabase.table("users").update({"last_login": now}).eq("id", user['id']).execute()
                
                return redirect(url_for('dashboard'))
            
        flash("ভুল ইমেইল অথবা পাসওয়ার্ড।", "danger")
    return render_template('login.html')
    
@app.route('/withdraw', methods=['GET', 'POST'])
@require_activation
def withdraw():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    balance = float(user['balance'])
    
    success_refs_query = supabase.table("referrals") \
        .select("id") \
        .eq("referrer_id", user_id) \
        .eq("status", "Success") \
        .execute().data
    success_ref_count = len(success_refs_query)
    
    meets_referral_cond = (success_ref_count >= 4)
    meets_balance_cond = (balance >= 350.00)
    can_withdraw = (meets_referral_cond and meets_balance_cond)
    
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        method = request.form.get('method')
        number = request.form.get('number')
        
        if not can_withdraw:
            flash("উইথড্র করার শর্তসমূহ পূরণ হয়নি।", "danger")
        elif amount < 350.00:
            flash("সর্বনিম্ন উইথড্রয়াল পরিমাণ ৩৫০ টাকা।", "danger")
        elif amount > balance:
            flash("আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই।", "danger")
        else:
            supabase.rpc("increment_balance", {"user_id": user_id, "amount": -amount}).execute()
            
            supabase.table("withdrawals").insert({
                "user_id": user_id,
                "amount": amount,
                "payment_method": method,
                "payment_number": number,
                "status": "Pending"
            }).execute()
            
            flash("উইথড্রয়াল অনুরোধ সফলভাবে সাবমিট হয়েছে।", "success")
            return redirect(url_for('withdraw'))
            
    history = supabase.table("withdrawals").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    return render_template('withdrawal.html', 
                           user=user, 
                           balance=balance,
                           success_ref_count=success_ref_count,
                           meets_referral_cond=meets_referral_cond,
                           meets_balance_cond=meets_balance_cond,
                           can_withdraw=can_withdraw,
                           history=history)
    
    

@app.route('/store')
def store():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("balance").eq("id", user_id).execute().data[0]
    premium_pkgs = supabase.table("packages").select("*").eq("is_premium", True).order("cost", desc=False).execute().data
    
    deposit_history = supabase.table("deposits").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    purchase_history = supabase.table("user_packages") \
        .select("bought_at, packages(name, cost, is_premium)") \
        .eq("user_id", user_id).order("bought_at", desc=True).execute().data
    
    return render_template('store.html', 
                           balance=user['balance'], 
                           premium_packages=premium_pkgs,
                           deposit_history=deposit_history,
                           purchase_history=purchase_history)    
    
@app.route('/add-money', methods=['GET', 'POST'])
def add_money():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        amount = request.form.get('amount')
        method = request.form.get('method')
        tx_id = request.form.get('transaction_id')
        
        try:
            supabase.table("deposits").insert({
                "user_id": user_id,
                "amount": float(amount),
                "payment_method": method,
                "transaction_id": tx_id,
                "status": "Pending"
            }).execute()
            flash("অনুরোধ জমা হয়েছে। যাচাইকরণের পর ব্যালেন্স যোগ করা হবে।", "success")
        except Exception:
            flash("এই ট্রানজেকশন আইডিটি পূর্বে ব্যবহৃত হয়েছে।", "danger")
            
    history = supabase.table("deposits").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    return render_template('add_money.html', history=history)

@app.route('/register', methods=['GET', 'POST'])
def register():
    ref_by = request.args.get('ref', '')
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        referrer_code = request.form.get('referrer')
        device_fingerprint = request.form.get('device_fingerprint')
        device_name = request.form.get('device_name')

        ip_address = request.headers.get('x-forwarded-for', request.remote_addr)
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()

        # ১. সার্বিক ডিভাইস ফিঙ্গারপ্রিন্ট সিকিউরিটি (একই ব্রাউজার/ফিঙ্গারপ্রিন্ট থেকে একাধিক অ্যাকাউন্ট ব্লক)
        if device_fingerprint and device_fingerprint.strip() != "":
            fp_clean = device_fingerprint.strip().lower()
            if fp_clean not in ["undefined", "null", "none", ""] and len(fp_clean) > 4:
                if not fp_clean.startswith("fallback_") and not fp_clean.startswith("secure_fallback_"):
                    device_exists = supabase.table("users").select("id").eq("device_fingerprint", fp_clean).execute().data
                    if device_exists:
                        flash("নিরাপত্তা সতর্কতা: আপনার ডিভাইস থেকে ইতিমধ্যে একটি অ্যাকাউন্ট তৈরি করা হয়েছে। এক ডিভাইসে একটার বেশি একাউন্ট থাকা নিষেধ!", "danger")
                        return redirect(url_for('register', ref=ref_by))

        referrer_id = None
        referrer_device_name = None
        referrer_fingerprint = None
        initial_balance = 0.00

        # রেফারার কোড থাকলে রেফারকারীর ডিভাইসের তথ্য টেনে আনা
        if referrer_code and referrer_code.isdigit():
            ref_uid = int(referrer_code)
            referrer_res = supabase.table("users").select("id", "device_name", "device_fingerprint").eq("uid", ref_uid).execute()
            if referrer_res.data:
                referrer_id = referrer_res.data[0]['id']
                referrer_device_name = referrer_res.data[0].get('device_name')
                referrer_fingerprint = referrer_res.data[0].get('device_fingerprint')
                initial_balance = 50.00 # নতুন মেম্বার পাবেন ৫০ টাকা বোনাস

        # ২. রেফার করার সময় ডিভাইস নেম (Device Model/Name) ম্যাচ করলে সাথে সাথে রেজিস্ট্রেশন বাতিল করা
        if referrer_id:
            # ক. সেম ডিভাইস নেম (যেমন: iPhone 15 == iPhone 15) চেকিং
            if referrer_device_name and device_name:
                ref_dev_clean = referrer_device_name.strip().lower()
                my_dev_clean = device_name.strip().lower()
                
                if ref_dev_clean == my_dev_clean and ref_dev_clean != "":
                    flash(f"নিরাপত্তা সতর্কতা: রেফারার এবং আপনার ডিভাইসের মডেল ({device_name}) একই। এক ডিভাইসে একটার বেশি একাউন্ট থাকা নিষেধ!", "danger")
                    return redirect(url_for('register', ref=ref_by))

            # খ. সেম ডিভাইস ফিঙ্গারপ্রিন্ট চেকিং
            if referrer_fingerprint and device_fingerprint:
                ref_fp_clean = referrer_fingerprint.strip().lower()
                my_fp_clean = device_fingerprint.strip().lower()
                if ref_fp_clean == my_fp_clean and my_fp_clean not in ["undefined", "null", "none", ""] and not my_fp_clean.startswith("fallback_"):
                    flash("নিরাপত্তা সতর্কতা: আপনি একই ডিভাইস ব্যবহার করে নিজের রেফারের লিংকে অ্যাকাউন্ট খুলতে পারবেন না। এক ডিভাইসে একটার বেশি একাউন্ট থাকা নিষেধ!", "danger")
                    return redirect(url_for('register', ref=ref_by))

        hashed_password = generate_password_hash(password)

        user_data = {
            "username": username,
            "email": email,
            "password_hash": hashed_password,
            "balance": initial_balance,
            "device_fingerprint": device_fingerprint,
            "ip_address": ip_address,
            "device_name": device_name if device_name else "Unknown Device"
        }
        
        try:
            new_user_res = supabase.table("users").insert(user_data).execute()
            if new_user_res.data:
                new_user_id = new_user_res.data[0]['id']
                new_uid = new_user_res.data[0]['uid']
                
                free_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
                supabase.table("user_packages").insert({
                    "user_id": new_user_id,
                    "package_id": 1,
                    "expires_at": free_expiry.isoformat()
                }).execute()
                
                # ৩. রেফারেল রিওয়ার্ড প্রদান
                if referrer_id:
                    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    
                    if random.random() < 0.80:
                        status = "Success"
                        supabase.rpc("increment_balance", {"user_id": referrer_id, "amount": 15.00}).execute()
                        
                        supabase.table("transactions").insert({
                            "user_id": referrer_id,
                            "title": f"Referral Bonus (New UID: #{new_uid})",
                            "amount": 15.00
                        }).execute()
                    else:
                        status = "Failed"
                        
                    supabase.table("referrals").insert({
                        "referrer_id": referrer_id,
                        "referred_id": new_user_id,
                        "status": status,
                        "scheduled_payout_at": now_str,
                        "processed_at": now_str
                    }).execute()
                        
                flash("নিবন্ধন সফল হয়েছে। লগইন করুন।", "success")
                return redirect(url_for('login'))
        except Exception:
            flash("ইউজারনেম অথবা ইমেইলটি ইতিমধ্যে ব্যবহৃত হয়েছে।", "danger")
            
    return render_template('register.html', ref_by=ref_by)
    

    
@app.route('/claim-daily', methods=['POST'])
def claim_daily():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    try:
        user_query = supabase.table("users").select("last_daily_checkin").eq("id", user_id).execute()
        if not user_query.data:
            return jsonify({"status": "error", "message": "ব্যবহারকারী সনাক্ত করা যায়নি।"}), 404
            
        user = user_query.data[0]
        last_checkin_str = user.get('last_daily_checkin')
        
        now = datetime.datetime.now(datetime.timezone.utc)
        reward_amount = 5.00
        
        if last_checkin_str:
            last_checkin = datetime.datetime.fromisoformat(last_checkin_str.replace('Z', '+00:00'))
            cooldown = datetime.timedelta(hours=24)
            
            if now < last_checkin + cooldown:
                return jsonify({
                    "status": "error", 
                    "message": "আপনি ইতিমধ্যে আজকের ডেইলি বোনাস ক্লেইম করেছেন।"
                }), 400

        supabase.table("users").update({"last_daily_checkin": now.isoformat()}).eq("id", user_id).execute()
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": reward_amount}).execute()
        
        supabase.table("transactions").insert({
            "user_id": user_id,
            "title": "Daily Check-in Bonus claimed",
            "amount": reward_amount
        }).execute()
        
        return jsonify({
            "status": "success", 
            "message": f"ডেইলি চেক-ইন সফল! আপনার ব্যালেন্সে ৳ {reward_amount} যোগ করা হয়েছে।"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"ডাটাবেজ ত্রুটি: {str(e)}"}), 500
        
@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # মেয়াদোত্তীর্ণ প্যাকেজ ডিলিট
    try:
        supabase.table("user_packages").delete().eq("user_id", user_id).not_.is_("expires_at", "null").lt("expires_at", now.isoformat()).execute()
    except Exception as e:
        print("Package clean error:", e)
        
    try:
        user_res = supabase.table("users").select("*").eq("id", user_id).execute().data
        if not user_res:
            session.clear()
            return redirect(url_for('login'))
        user = user_res[0]
    except Exception as e:
        print("User fetch retry on dashboard:", e)
        user_res = create_client(SUPABASE_URL, SUPABASE_KEY).table("users").select("*").eq("id", user_id).execute().data
        if not user_res:
            session.clear()
            return redirect(url_for('login'))
        user = user_res[0]

    balance = float(user.get('balance', 0))
    
    # ডেইলি চেক-ইন ভ্যালিডেশন
    is_daily_eligible = True
    last_checkin_str = user.get('last_daily_checkin')
    if last_checkin_str:
        try:
            last_checkin = datetime.datetime.fromisoformat(last_checkin_str.replace('Z', '+00:00'))
            cooldown = datetime.timedelta(hours=24)
            if now < last_checkin + cooldown:
                is_daily_eligible = False
        except Exception:
            pass
    
    # সক্রিয় প্যাকেজ তালিকা রিট্রিভ
    all_pkgs = []
    try:
        pkg_res = supabase.table("user_packages") \
            .select("id, last_claimed_at, expires_at, packages(name, duration_hours, yield_amount, is_premium)") \
            .eq("user_id", user_id).execute()
        all_pkgs = pkg_res.data or []
    except Exception as e:
        print("Package fetch error:", e)
        try:
            pkg_res = create_client(SUPABASE_URL, SUPABASE_KEY).table("user_packages") \
                .select("id, last_claimed_at, expires_at, packages(name, duration_hours, yield_amount, is_premium)") \
                .eq("user_id", user_id).execute()
            all_pkgs = pkg_res.data or []
        except Exception:
            all_pkgs = []
        
    # সেলফ-হিলিং: প্যাকেজ না থাকলে ফ্রি প্যাকেজ সক্রিয় করা
    if not all_pkgs:
        try:
            free_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
            supabase.table("user_packages").insert({
                "user_id": user_id,
                "package_id": 1,
                "expires_at": free_expiry.isoformat()
            }).execute()
            
            pkg_res = supabase.table("user_packages") \
                .select("id, last_claimed_at, expires_at, packages(name, duration_hours, yield_amount, is_premium)") \
                .eq("user_id", user_id).execute()
            all_pkgs = pkg_res.data or []
        except Exception:
            pass

    owned_pkgs = [p for p in all_pkgs if p.get('packages')]
    
    notice = "সবাইকে টেলিগ্রাম চ্যানেলে জয়েন হওয়ার জন্য অনুরোধ করা হলো, যাদের টেলিগ্রাম নেই তারা আপডেট পেজ একবার ঘুরে আসুন!"
    return render_template('dashboard.html', 
                           user=user, 
                           owned_packages=owned_pkgs, 
                           notice=notice,
                           is_daily_eligible=is_daily_eligible)


@app.route('/buy-package', methods=['POST'])
def buy_package():
    user_id = session.get('user_id')
    package_id = request.form.get('package_id')
    if not user_id:
        return redirect(url_for('login'))
        
    pkg = supabase.table("packages").select("*").eq("id", package_id).execute()
    if not pkg.data:
        flash("প্যাকেজ পাওয়া যায়নি।", "danger")
        return redirect(url_for('store'))
        
    cost = float(pkg.data[0]['cost'])
    pkg_name = pkg.data[0]['name']
    
    user = supabase.table("users").select("balance").eq("id", user_id).execute().data[0]
    balance = float(user['balance'])
    
    if balance >= cost:
        supabase.table("user_packages").delete().eq("user_id", user_id).eq("package_id", 1).execute()
        
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": -cost}).execute()
        
        expiry_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
        
        supabase.table("user_packages").insert({
            "user_id": user_id,
            "package_id": package_id,
            "last_claimed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "expires_at": expiry_date.isoformat()
        }).execute()
        
        flash(f"{pkg_name} প্যাকেজটি সফলভাবে সক্রিয় করা হয়েছে। মেয়াদ ৩০ দিন।", "success")
    else:
        shortage = cost - balance
        flash(f"ব্যালেন্স অপর্যাপ্ত! {pkg_name} প্যাকেজটি কিনতে আপনার আরও ৳ {shortage:.2f} লাগবে। দয়া করে এড মানি করুন।", "danger")
        
    return redirect(url_for('store'))
    
@app.route('/claim-mining', methods=['POST'])
def claim_mining():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    user_package_id = request.json.get('user_package_id')
    if not user_package_id:
        return jsonify({"status": "error", "message": "অবৈধ মাইনিং রিকোয়েস্ট।"}), 400
        
    pkg_query = supabase.table("user_packages") \
        .select("id, last_claimed_at, expires_at, packages(name, yield_amount, duration_hours)") \
        .eq("id", user_package_id).eq("user_id", user_id).execute().data
        
    if not pkg_query:
        return jsonify({"status": "error", "message": "প্যাকেজটি পাওয়া যায়নি বা মেয়াদ শেষ হয়ে গেছে।"}), 404
        
    record = pkg_query[0]
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if record.get('expires_at'):
        expires_at = datetime.datetime.fromisoformat(record['expires_at'].replace('Z', '+00:00'))
        if now > expires_at:
            supabase.table("user_packages").delete().eq("id", user_package_id).execute()
            return jsonify({"status": "error", "message": "এই মাইনিং packagesটির মেয়াদ শেষ হয়ে গেছে।"}), 400
            
    last_claim = datetime.datetime.fromisoformat(record['last_claimed_at'].replace('Z', '+00:00'))
    cooldown = datetime.timedelta(hours=record['packages']['duration_hours'])
    
    if now >= last_claim + cooldown:
        supabase.table("user_packages").update({"last_claimed_at": now.isoformat()}).eq("id", user_package_id).execute()
        yield_amount = float(record['packages']['yield_amount'])
        
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": yield_amount}).execute()
        
        supabase.table("transactions").insert({
            "user_id": user_id,
            "title": f"Mining Yield Claimed: {record['packages']['name']}",
            "amount": yield_amount
        }).execute()
        
        return jsonify({"status": "success", "message": f"৳ {yield_amount} সফলভাবে ক্লেইমড!"})
    else:
        return jsonify({"status": "error", "message": "এই নোডের মাইনিং প্রসেস এখনও সম্পন্ন হয়নি।"})





# ১. অ্যাডস শেয়ার টাস্ক তালিকা রাউট
@app.route('/adshear')
@require_activation
def adshear_list():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    # সমস্ত সক্রিয় অ্যাডস শেয়ার টাস্ক
    all_ads_tasks = supabase.table("adshear_tasks").select("*").order("created_at", desc=True).execute().data or []
    
    # ইউজারের সাবমিট করা কাজসমূহ
    user_submissions = supabase.table("adshear_submissions").select("task_id, status").eq("user_id", user_id).execute().data or []
    user_sub_map = {s['task_id']: s['status'] for s in user_submissions}
    
    # ইউজারের জন্য লকড টাস্ক আইডি সেট করা
    locked_ids_for_user = set()
    for sub in user_submissions:
        if sub['status'] in ['Pending', 'Approved']:
            # সাবমিট করা টাস্কটির locked_task_ids চেক
            matching_task = next((t for t in all_ads_tasks if str(t['id']) == str(sub['task_id'])), None)
            if matching_task and matching_task.get('locked_task_ids'):
                raw_ids = str(matching_task['locked_task_ids']).split(',')
                for rid in raw_ids:
                    cleaned = rid.strip()
                    if cleaned.isdigit():
                        locked_ids_for_user.add(int(cleaned))

    # সর্বমোট সাবমিশন কাউন্ট (লিমিট চেকের জন্য)
    all_active_subs = supabase.table("adshear_submissions").select("task_id").neq("status", "Rejected").execute().data or []
    task_counts = {}
    for sub in all_active_subs:
        tid = sub['task_id']
        task_counts[tid] = task_counts.get(tid, 0) + 1

    enhanced_tasks = []
    for task in all_ads_tasks:
        tid = task['id']
        sub_count = task_counts.get(tid, 0)
        max_limit = task.get('max_submissions') or 0
        
        is_limit_reached = (max_limit > 0 and sub_count >= max_limit)
        is_locked = (tid in locked_ids_for_user)
        user_status = user_sub_map.get(tid)
        
        enhanced_tasks.append({
            **task,
            'sub_count': sub_count,
            'is_limit_reached': is_limit_reached,
            'is_locked': is_locked,
            'user_status': user_status
        })
            
    return render_template('adshear.html', user=user, all_ads_tasks=enhanced_tasks)


# ২. অ্যাডস ডিটেইলস ও লিংক সাবমিশন পেজ
@app.route('/adshear/<task_id>')
def adshear_detail(task_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("username").eq("id", user_id).execute().data[0]
    
    task_query = supabase.table("adshear_tasks").select("*").eq("id", task_id).execute().data
    if not task_query:
        flash("অ্যাড টাস্কটি খুঁজে পাওয়া যায়নি।", "danger")
        return redirect(url_for('adshear_list'))
        
    task = task_query[0]
    
    # সাবমিশন তথ্য
    submission_query = supabase.table("adshear_submissions") \
        .select("status, proof_link") \
        .eq("user_id", user_id).eq("task_id", task_id).execute().data
        
    status = submission_query[0]['status'] if submission_query else None
    proof_link = submission_query[0]['proof_link'] if submission_query else None
    
    # লিমিট চেক
    sub_count_res = supabase.table("adshear_submissions").select("id", count="exact").eq("task_id", task_id).neq("status", "Rejected").execute()
    current_subs = sub_count_res.count if sub_count_res.count is not None else 0
    max_limit = task.get('max_submissions') or 0
    is_limit_reached = (max_limit > 0 and current_subs >= max_limit)

    return render_template('adshear_detail.html', task=task, status=status, proof_link=proof_link, sub_count=current_subs, is_limit_reached=is_limit_reached)


@app.route('/adshear/submit', methods=['POST'])
def submit_adshear():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    task_id = request.form.get('task_id')
    proof_link = str(request.form.get('proof_link', '')).strip()
    
    # ১. ইউজার http/https না লিখলেও স্বয়ংক্রিয়ভাবে https:// প্রিফিক্স যোগ করা
    if proof_link and not (proof_link.startswith("http://") or proof_link.startswith("https://")):
        proof_link = "https://" + proof_link
        
    # ২. কঠোর ফেসবুক লিঙ্ক ভ্যালিডেশন (Regex Validation)
    fb_pattern = r'^(https?:\/\/)?(www\.|m\.|web\.)?(facebook\.com|fb\.com|fb\.watch)\/.+$'
    
    if not proof_link or len(proof_link) < 12 or not re.match(fb_pattern, proof_link, re.IGNORECASE):
        flash("ভুল লিংক! দয়া করে একটি সঠিক ফেসবুক পোস্টের লিঙ্ক (যেমন: https://facebook.com/groups/...) প্রদান করুন।", "danger")
        return redirect(url_for('adshear_detail', task_id=task_id))

    try:
        # ৩. টাস্ক অস্তিত্ব ও সর্বোচ্চ লিমিট চেক
        task_res = supabase.table("adshear_tasks").select("*").eq("id", task_id).execute().data
        if not task_res:
            flash("টাস্ক আইডি খুঁজে পাওয়া যায়নি।", "danger")
            return redirect(url_for('adshear_list'))
            
        task = task_res[0]
        max_limit = int(task.get('max_submissions') or 0)
        
        if max_limit > 0:
            sub_count_res = supabase.table("adshear_submissions").select("id", count="exact").eq("task_id", task_id).neq("status", "Rejected").execute()
            current_subs = sub_count_res.count if sub_count_res.count is not None else 0
            if current_subs >= max_limit:
                flash("দুঃখিত, এই ক্যাম্পেইনের নির্ধারিত লিমিট পূর্ণ হয়ে গেছে!", "danger")
                return redirect(url_for('adshear_list'))

        # ৪. পূর্বের ডুপ্লিকেট রেকর্ড ডিলিট করে নতুন পেন্ডিং ইনসার্ট
        supabase.table("adshear_submissions").delete() \
            .eq("user_id", user_id).eq("task_id", task_id).execute()
            
        insert_payload = {
            "user_id": user_id,
            "task_id": int(task_id) if str(task_id).isdigit() else task_id,
            "proof_link": proof_link,
            "proof_image_url": proof_link,
            "status": "Pending"
        }
        
        supabase.table("adshear_submissions").insert(insert_payload).execute()
        flash("ফেসবুক পোস্ট লিংক সফলভাবে জমা দেওয়া হয়েছে! এডমিন দ্রুত ভেরিফাই করে রিওয়ার্ড যোগ করবে।", "success")
        return redirect(url_for('adshear_list'))
        
    except Exception as e:
        print("AdShare Submit Error:", e)
        flash("লিংক সাবমিট করতে সমস্যা হয়েছে। দয়া করে আবার চেষ্টা করুন।", "danger")
        return redirect(url_for('adshear_detail', task_id=task_id))
    
@app.route('/admin/adshear', methods=['GET', 'POST'])
def admin_adshear():
    if not check_admin_auth():
        flash("Unauthorized Access", "danger")
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        caption = request.form.get('caption')
        image_url = request.form.get('image_url')
        reward = float(request.form.get('reward', 0))
        max_submissions = int(request.form.get('max_submissions', 0))
        locked_task_ids = request.form.get('locked_task_ids', '').strip()
        
        try:
            supabase.table("adshear_tasks").insert({
                "title": title,
                "caption": caption,
                "image_url": image_url,
                "reward": reward,
                "max_submissions": max_submissions,
                "locked_task_ids": locked_task_ids
            }).execute()
            flash("নতুন অ্যাডস শেয়ার ক্যাম্পেইনটি সফলভাবে যুক্ত হয়েছে।", "success")
        except Exception as e:
            print("Ad Campaign Create Error:", e)
            flash("ক্যাম্পেইন তৈরি করতে সমস্যা হয়েছে।", "danger")
            
        return redirect(url_for('admin_adshear'))
        
    # --- পেজিনেশন ও ক্রনোলজিক্যাল ওল্ডেস্ট-ফার্স্ট সর্টিং (Oldest Submissions First) ---
    page = int(request.args.get('page', 1))
    limit = 20
    start = (page - 1) * limit
    end = start + limit - 1
    
    pending = []
    total_count = 0
    
    try:
        count_res = supabase.table("adshear_submissions").select("id", count="exact").eq("status", "Pending").execute()
        total_count = count_res.count if count_res.count is not None else 0

        # desc=False দেওয়া হয়েছে যাতে সবচেয়ে পুরানো পেন্ডিং পোস্ট সবার আগে আসে
        raw_subs = supabase.table("adshear_submissions") \
            .select("*") \
            .eq("status", "Pending") \
            .order("created_at", desc=False) \
            .range(start, end).execute().data or []
            
        for sub in raw_subs:
            u_res = supabase.table("users").select("username, email, uid").eq("id", sub['user_id']).execute().data
            t_res = supabase.table("adshear_tasks").select("title, reward").eq("id", sub['task_id']).execute().data
            
            sub['users'] = u_res[0] if u_res else {'username': 'Unknown', 'email': '', 'uid': '0'}
            sub['adshear_tasks'] = t_res[0] if t_res else {'title': 'Ad Task', 'reward': 0}
            pending.append(sub)
    except Exception as err:
        print("Error fetching adshare pending submissions:", err)
        
    total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1
        
    return render_template('admin_adshear.html', 
                           pending_submissions=pending,
                           total_count=total_count,
                           page=page,
                           has_next=has_next,
                           has_prev=has_prev)
    
# ৫. এডমিন অ্যাডস শেয়ার এপ্রুভ / রিজেক্ট অ্যাকশন রাউট (/admin/adshear/action)
@app.route('/admin/adshear/action', methods=['POST'])
def admin_adshear_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    submission_id = request.form.get('submission_id')
    action = request.form.get('action') # 'approve' or 'reject'
    
    if not submission_id or not action:
        flash("অবৈধ অনুরোধ।", "danger")
        return redirect(url_for('admin_adshear'))
        
    try:
        # ১. সাবমিশন রেকর্ড রিট্রিভ করা
        sub_query = supabase.table("adshear_submissions").select("*").eq("id", submission_id).execute().data
        if not sub_query:
            flash("রেকর্ড খুঁজে পাওয়া যায়নি।", "danger")
            return redirect(url_for('admin_adshear'))
            
        sub = sub_query[0]
        target_user_id = sub['user_id']
        task_id = sub['task_id']
        
        # ২. সম্পর্কিত টাস্কের রিওয়ার্ড ও টাইটেল ম্যানুয়ালি টেনে আনা (Foreign Key error মুক্ত)
        task_query = supabase.table("adshear_tasks").select("title, reward").eq("id", task_id).execute().data
        reward = float(task_query[0]['reward']) if task_query else 0.00
        task_title = task_query[0]['title'] if task_query else "Ad Share Task"
        
        if action == 'approve':
            # ক. ডাটাবেজে স্ট্যাটাস Approved করা
            supabase.table("adshear_submissions").update({"status": "Approved"}).eq("id", submission_id).execute()
            
            # খ. ইউজারের মূল ব্যালেন্সে রিওয়ার্ড বোনাস যোগ করা
            if reward > 0:
                supabase.rpc("increment_balance", {"user_id": target_user_id, "amount": reward}).execute()
                
                # গ. ট্রানজেকশন হিস্ট্রি সেভ করা
                supabase.table("transactions").insert({
                    "user_id": target_user_id,
                    "title": f"Ad Share Approved: {task_title}",
                    "amount": reward
                }).execute()
                
            flash("কাজটি সফলভাবে এপ্রুভ করা হয়েছে এবং ইউজারের ব্যালেন্সে রিওয়ার্ড যোগ হয়েছে।", "success")
            
        elif action == 'reject':
            # স্ট্যাটাস Rejected করা
            supabase.table("adshear_submissions").update({"status": "Rejected"}).eq("id", submission_id).execute()
            flash("কাজটি বাতিল (Rejected) করা হয়েছে।", "success")
            
    except Exception as e:
        print("AdShare Action Error:", str(e))
        flash("অ্যাকশন প্রসেস করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।", "danger")
        
    return redirect(url_for('admin_adshear'))

@app.route('/reviews', methods=['GET', 'POST'])
def reviews_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user_res = supabase.table("users").select("*").eq("id", user_id).execute().data
    if not user_res:
        session.clear()
        return redirect(url_for('login'))
        
    user = user_res[0]
    is_admin = user.get('is_admin', False)
    
    if request.method == 'POST':
        comment = request.form.get('comment')
        rating = int(request.form.get('rating', 5))
        image_url = request.form.get('image_url')
        
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        insert_data = {
            "user_id": user_id,
            "reviewer_name": user['username'],
            "rating": rating,
            "comment": comment,
            "is_admin_fake": False,
            "created_at": now_str
        }
        
        if image_url and image_url.strip() != "":
            insert_data["image_url"] = image_url.strip()
            
        try:
            supabase.table("reviews").insert(insert_data).execute()
            flash("আপনার মূল্যবান মতামতটি সফলভাবে জমা হয়েছে।", "success")
        except Exception as e:
            print("Review Insert Error:", e)
            flash("রিভিউ জমা দিতে ত্রুটি ঘটেছে। অনুগ্রহ করে আবার চেষ্টা করুন।", "danger")
            
        return redirect(url_for('reviews_page'))
        
    # --- ১০০% গ্যারান্টেড Newest-First সর্টিং লজিক ---
    try:
        if is_admin:
            reviews_data = supabase.table("reviews").select("*").order("created_at", desc=True).execute().data or []
        else:
            fake_reviews = supabase.table("reviews").select("*").eq("is_admin_fake", True).order("created_at", desc=True).execute().data or []
            my_reviews = supabase.table("reviews").select("*").eq("user_id", user_id).eq("is_admin_fake", False).order("created_at", desc=True).execute().data or []
            reviews_data = fake_reviews + my_reviews
            
        # পাইথনের নিরাপদ টাইমস্ট্যাম্প সর্টার (সর্বশেষ নতুন রিভিউ সবার আগে আসবে)
        def parse_sort_date(item):
            d_str = item.get('created_at', '')
            if not d_str:
                return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
            try:
                clean_str = d_str.replace('Z', '+00:00')
                return datetime.datetime.fromisoformat(clean_str)
            except Exception:
                return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
                
        reviews_data.sort(key=parse_sort_date, reverse=True)
    except Exception as e:
        print("Review Fetch Error:", e)
        reviews_data = []
            
    return render_template('reviews.html', user=user, reviews=reviews_data, is_admin=is_admin)
    
@app.route('/admin/reviews/create', methods=['POST'])
def admin_create_fake_review():
    user_id = session.get('user_id')
    if not user_id or not check_admin_auth():
        return "Unauthorized Action", 403
        
    fake_name = request.form.get('fake_name')
    rating = int(request.form.get('rating', 5))
    comment = request.form.get('comment')
    image_url = request.form.get('image_url')
    custom_date = request.form.get('custom_date')
    
    review_data = {
        "reviewer_name": fake_name,
        "rating": rating,
        "comment": comment,
        "is_admin_fake": True
    }
    
    if image_url and image_url.strip() != "":
        review_data["image_url"] = image_url.strip()
        
    if custom_date:
        try:
            parsed_date = datetime.datetime.strptime(custom_date, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
            review_data["created_at"] = parsed_date.isoformat()
        except Exception as date_err:
            print("Date Parse Error:", date_err)
            
    try:
        supabase.table("reviews").insert(review_data).execute()
        flash("ফেক রিভিউটি সফলভাবে লাইভ করা হয়েছে।", "success")
    except Exception as e:
        error_msg = str(e)
        flash(f"ডাটাবেজ ত্রুটি: {error_msg}", "danger")
        print("Database Insert Error:", error_msg)
        
    return redirect(url_for('reviews_page'))


@app.route('/admin/reviews/delete', methods=['POST'])
def admin_delete_review():
    user_id = session.get('user_id')
    if not user_id or not check_admin_auth():
        return "Unauthorized Action", 403
        
    review_id = request.form.get('review_id')
    try:
        supabase.table("reviews").delete().eq("id", review_id).execute()
        flash("রিভিউটি সফলভাবে ডিলিট করা হয়েছে।", "success")
    except Exception:
        flash("রিভিউটি ডিলিট করা যায়নি।", "danger")
        
    return redirect(url_for('reviews_page'))
    
# ৮. লগআউট
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
