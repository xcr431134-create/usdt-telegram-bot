import os
import telebot
import sqlite3
import threading
from flask import Flask
import logging
import time
from datetime import datetime, timedelta

# ✅ تفعيل السجلات المفصلة
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 50)
print("🔍 بدء تشخيص البوت...")
print("=" * 50)

# فحص BOT_TOKEN
BOT_TOKEN = os.environ.get('BOT_TOKEN')
print(f"🔑 BOT_TOKEN موجود: {'✅ نعم' if BOT_TOKEN else '❌ لا'}")

if not BOT_TOKEN:
    print("❌ خطأ: BOT_TOKEN غير موجود في environment variables!")
    exit(1)

# 🎯 تعريف البوت هنا في البداية مباشرة
try:
    bot = telebot.TeleBot(BOT_TOKEN)
    print("✅ تم إنشاء كائن البوت بنجاح")
except Exception as e:
    print(f"❌ فشل في إنشاء البوت: {e}")
    exit(1)

# ======================
# 🔐 إعدادات المشرفين
# ======================

ADMINS = ['8400225549']  # قائمة IDs المشرفين

def is_admin(user_id):
    """التحقق إذا المستخدم مشرف"""
    return str(user_id) in ADMINS

# ======================
# 🗄️ نظام SQLite معدل
# ======================

DB_FILE = os.path.join(os.getcwd(), 'usdt_bot.db')
db_lock = threading.Lock()

# مستويات VIP
VIP_LEVELS = {
    0: {"name": "🟢 مبتدئ", "daily_bonus": 0.8, "max_attempts": 3},
    1: {"name": "🔵 متقدم", "daily_bonus": 1.5, "max_attempts": 5},
    2: {"name": "🟣 محترف", "daily_bonus": 2.5, "max_attempts": 8},
    3: {"name": "🟠 خبير", "daily_bonus": 4.0, "max_attempts": 12},
    4: {"name": "🔴 ماستر", "daily_bonus": 6.0, "max_attempts": 18}
}

def init_database():
    """تهيئة قاعدة البيانات"""
    try:
        print(f"📁 محاولة إنشاء قاعدة بيانات في: {DB_FILE}")
        
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        # إنشاء الجدول الرئيسي للمستخدمين
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0.0,
                referral_count INTEGER DEFAULT 0,
                new_referrals INTEGER DEFAULT 0,
                vip_level INTEGER DEFAULT 0,
                attempts INTEGER DEFAULT 0,
                total_earnings REAL DEFAULT 0.0,
                total_deposits REAL DEFAULT 0.0,
                registration_date TEXT,
                last_activity TEXT,
                last_mining_date TEXT,
                referral_bonus_claimed BOOLEAN DEFAULT FALSE
            )
        """)
        
        conn.commit()
        conn.close()
        print(f"✅ تم تهيئة قاعدة البيانات بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        return False

def get_db_connection():
    """إنشاء اتصال آمن بقاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ فشل في الاتصال بقاعدة البيانات: {e}")
        return None

def get_user(user_id):
    """جلب أو إنشاء مستخدم"""
    with db_lock:
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                return None
                
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
            user_data = cursor.fetchone()
            
            if user_data:
                user_dict = dict(user_data)
                return user_dict
            else:
                # إنشاء مستخدم جديد
                user_dict = {
                    'user_id': str(user_id),
                    'username': "",
                    'first_name': "",
                    'balance': 0.0,
                    'referral_count': 0,
                    'new_referrals': 0,
                    'vip_level': 0,
                    'attempts': 3,  # محاولات أساسية
                    'total_earnings': 0.0,
                    'total_deposits': 0.0,
                    'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'last_activity': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'last_mining_date': None,
                    'referral_bonus_claimed': False
                }
                
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, balance, referral_count, 
                    new_referrals, vip_level, attempts, total_earnings, total_deposits, 
                    registration_date, last_activity, last_mining_date, referral_bonus_claimed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_dict['user_id'], user_dict['username'], user_dict['first_name'],
                    user_dict['balance'], user_dict['referral_count'], user_dict['new_referrals'],
                    user_dict['vip_level'], user_dict['attempts'], user_dict['total_earnings'],
                    user_dict['total_deposits'], user_dict['registration_date'], 
                    user_dict['last_activity'], user_dict['last_mining_date'],
                    user_dict['referral_bonus_claimed']
                ))
                
                conn.commit()
                print(f"✅ تم إنشاء مستخدم جديد: {user_id}")
                return user_dict
                
        except Exception as e:
            print(f"❌ خطأ في جلب بيانات المستخدم: {e}")
            return None
        finally:
            if conn:
                conn.close()

def update_user(user_id, **kwargs):
    """تحديث بيانات المستخدم"""
    with db_lock:
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(str(user_id))
            
            cursor.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
            conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ خطأ في تحديث المستخدم: {e}")
            return False
        finally:
            if conn:
                conn.close()

def get_mining_time_left(user_id):
    """حساب الوقت المتبقي للمكافأة اليومية"""
    user = get_user(user_id)
    if not user or not user['last_mining_date']:
        return "جاهز الآن! ✅"
    
    last_mining = datetime.strptime(user['last_mining_date'], '%Y-%m-%d %H:%M:%S')
    next_mining = last_mining + timedelta(hours=24)
    now = datetime.now()
    
    if now >= next_mining:
        return "جاهز الآن! ✅"
    
    time_left = next_mining - now
    hours = time_left.seconds // 3600
    minutes = (time_left.seconds % 3600) // 60
    return f"{hours:02d}س {minutes:02d}د ⏳"

def get_days_since_registration(user_id):
    """حساب عدد الأيام منذ التسجيل"""
    user = get_user(user_id)
    if not user:
        return 0
    
    reg_date = datetime.strptime(user['registration_date'], '%Y-%m-%d %H:%M:%S')
    now = datetime.now()
    days = (now - reg_date).days
    return max(0, days)

def claim_daily_bonus(user_id):
    """المطالبة بالمكافأة اليومية"""
    user = get_user(user_id)
    if not user:
        return False, "❌ المستخدم غير موجود"
    
    # التحقق إذا المكافأة جاهزة
    time_left = get_mining_time_left(user_id)
    if "جاهز" not in time_left:
        return False, f"⏰ لم يحن وقت المكافأة بعد\nالوقت المتبقي: {time_left}"
    
    # إضافة المكافأة
    bonus_amount = VIP_LEVELS[user['vip_level']]['daily_bonus']
    new_balance = user['balance'] + bonus_amount
    new_earnings = user['total_earnings'] + bonus_amount
    
    success = update_user(
        user_id,
        balance=new_balance,
        total_earnings=new_earnings,
        last_mining_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    if success:
        return True, f"✅ تم استلام المكافأة اليومية: {bonus_amount} USDT"
    else:
        return False, "❌ خطأ في استلام المكافأة"

def get_user_profile(user_id, first_name="", username=""):
    """إنشاء نص الملف الشخصي"""
    user = get_user(user_id)
    if not user:
        return "❌ المستخدم غير موجود"
    
    # تحديث النشاط
    update_user(
        user_id,
        first_name=first_name,
        username=username or "",
        last_activity=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    # حساب الإحالات المطلوبة
    referrals_needed = max(0, 10 - user['referral_count'])
    
    # معلومات VIP
    vip_info = VIP_LEVELS[user['vip_level']]
    max_profit = vip_info['max_attempts'] * 1.0  # 1 USDT لكل محاولة كحد أقصى
    
    profile = f"📊 **الملف الشخصي**\n\n"
    profile += f"👤 المستخدم: {user['first_name'] or 'غير معروف'}\n"
    profile += f"🆔 المعرف: {user['user_id']}\n"
    profile += f"💰 الرصيد: **{user['balance']:.2f} USDT**\n"
    profile += f"👥 الإحالات: **{user['referral_count']} مستخدم** (مطلوب {referrals_needed})\n"
    profile += f"📈 الإحالات الجديدة: **{user['new_referrals']}/1** (جائزة: 1 USDT + محاولة)\n"
    profile += f"🏆 مستوى VIP: {vip_info['name']}\n"
    profile += f"🎯 المحاولات المتبقية: **{user['attempts']}** ({vip_info['max_attempts']} أساسية + {max(0, user['attempts'] - vip_info['max_attempts'])} إضافية)\n"
    profile += f"📅 أيام التسجيل: **{get_days_since_registration(user_id)} يوم**\n\n"
    
    profile += f"⏰ مكافأة التعدين: {get_mining_time_left(user_id)}\n\n"
    
    profile += f"💎 إجمالي الأرباح: **{user['total_earnings']:.2f} USDT**\n"
    profile += f"💳 إجمالي الإيداعات: **{user['total_deposits']:.2f} USDT**\n"
    profile += f"📅 تاريخ التسجيل: {user['registration_date']}"
    
    return profile

# ======================
# 🛠️ الأوامر الإدارية - بنفس الصيغة المطلوبة
# ======================

@bot.message_handler(commands=['quickadd'])
def handle_quickadd(message):
    """💰 إضافة رصيد - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /quickadd [user_id] [amount]")
            return
        
        target_user_id = parts[1]
        amount = float(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        new_balance = user['balance'] + amount
        success = update_user(target_user_id, balance=new_balance)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم إضافة {amount} USDT للمستخدم {target_user_id}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إضافة الرصيد!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setbalance'])
def handle_setbalance(message):
    """💰 تعيين رصيد محدد - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /setbalance [user_id] [amount]")
            return
        
        target_user_id = parts[1]
        amount = float(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        success = update_user(target_user_id, balance=amount)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين رصيد المستخدم {target_user_id} إلى {amount} USDT")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين الرصيد!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setreferrals'])
def handle_setreferrals(message):
    """👥 تعيين عدد الإحالات - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /setreferrals [user_id] [count]")
            return
        
        target_user_id = parts[1]
        count = int(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        success = update_user(target_user_id, referral_count=count)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين إحالات المستخدم {target_user_id} إلى {count}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين الإحالات!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['addreferral'])
def handle_addreferral(message):
    """👥 إضافة إحالة واحدة - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "📝 usage: /addreferral [user_id]")
            return
        
        target_user_id = parts[1]
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        new_count = user['referral_count'] + 1
        success = update_user(target_user_id, referral_count=new_count)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم إضافة إحالة للمستخدم {target_user_id}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إضافة الإحالة!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setattempts'])
def handle_setattempts(message):
    """🎯 تعيين محاولات الألعاب - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /setattempts [user_id] [attempts]")
            return
        
        target_user_id = parts[1]
        attempts = int(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        success = update_user(target_user_id, attempts=attempts)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين محاولات المستخدم {target_user_id} إلى {attempts}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين المحاولات!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['resetattempts'])
def handle_resetattempts(message):
    """🎯 إعادة تعيين المحاولات - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "📝 usage: /resetattempts [user_id]")
            return
        
        target_user_id = parts[1]
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        vip_info = VIP_LEVELS[user['vip_level']]
        base_attempts = vip_info['max_attempts']
        
        success = update_user(target_user_id, attempts=base_attempts)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم إعادة تعيين محاولات المستخدم {target_user_id} إلى {base_attempts}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إعادة تعيين المحاولات!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['addattempts'])
def handle_addattempts(message):
    """🎯 إضافة محاولات - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /addattempts [user_id] [count]")
            return
        
        target_user_id = parts[1]
        count = int(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        new_attempts = user['attempts'] + count
        success = update_user(target_user_id, attempts=new_attempts)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم إضافة {count} محاولة للمستخدم {target_user_id}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إضافة المحاولات!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setdeposits'])
def handle_setdeposits(message):
    """💳 تعيين إجمالي الإيداعات - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /setdeposits [user_id] [amount]")
            return
        
        target_user_id = parts[1]
        amount = float(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        success = update_user(target_user_id, total_deposits=amount)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين إيداعات المستخدم {target_user_id} إلى {amount} USDT")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين الإيداعات!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['adddeposit'])
def handle_adddeposit(message):
    """💳 إضافة إيداع - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /adddeposit [user_id] [amount]")
            return
        
        target_user_id = parts[1]
        amount = float(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        new_deposits = user['total_deposits'] + amount
        success = update_user(target_user_id, total_deposits=new_deposits)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم إضافة إيداع {amount} USDT للمستخدم {target_user_id}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إضافة الإيداع!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['userinfo'])
def handle_userinfo(message):
    """📊 معلومات كاملة عن المستخدم - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "📝 usage: /userinfo [user_id]")
            return
        
        target_user_id = parts[1]
        user = get_user(target_user_id)
        
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        vip_info = VIP_LEVELS[user['vip_level']]
        
        info_msg = f"👤 معلومات المستخدم:\n\n"
        info_msg += f"🆔 المعرف: {user['user_id']}\n"
        info_msg += f"👤 الاسم: {user['first_name'] or 'غير معروف'}\n"
        info_msg += f"💰 الرصيد: {user['balance']:.2f} USDT\n"
        info_msg += f"👥 الإحالات: {user['referral_count']}\n"
        info_msg += f"🏆 مستوى VIP: {vip_info['name']}\n"
        info_msg += f"🎯 المحاولات: {user['attempts']}\n"
        info_msg += f"💎 إجمالي الأرباح: {user['total_earnings']:.2f} USDT\n"
        info_msg += f"💳 إجمالي الإيداعات: {user['total_deposits']:.2f} USDT\n"
        info_msg += f"📅 تاريخ التسجيل: {user['registration_date']}"
        
        bot.send_message(message.chat.id, info_msg)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['listusers'])
def handle_listusers(message):
    """📊 قائمة جميع المستخدمين - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        conn = get_db_connection()
        if not conn:
            bot.send_message(message.chat.id, "❌ خطأ في قاعدة البيانات!")
            return
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()['total']
        
        cursor.execute("SELECT user_id, first_name, balance FROM users ORDER BY registration_date DESC LIMIT 20")
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            bot.send_message(message.chat.id, "❌ لا يوجد مستخدمين!")
            return
        
        users_msg = f"👥 قائمة المستخدمين (آخر 20 من أصل {total_users}):\n\n"
        
        for i, user in enumerate(users, 1):
            users_msg += f"{i}. {user['first_name'] or 'غير معروف'} (ID: {user['user_id']})\n"
            users_msg += f"   💰 {user['balance']:.2f} USDT\n\n"
        
        bot.send_message(message.chat.id, users_msg)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['stats'])
def handle_stats(message):
    """📊 إحصائيات البوت - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        conn = get_db_connection()
        if not conn:
            bot.send_message(message.chat.id, "❌ خطأ في قاعدة البيانات!")
            return
        
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total_users FROM users")
        total_users = cursor.fetchone()['total_users']
        
        cursor.execute("SELECT SUM(balance) as total_balance FROM users")
        total_balance = cursor.fetchone()['total_balance'] or 0
        
        cursor.execute("SELECT SUM(total_earnings) as total_earnings FROM users")
        total_earnings = cursor.fetchone()['total_earnings'] or 0
        
        cursor.execute("SELECT SUM(total_deposits) as total_deposits FROM users")
        total_deposits = cursor.fetchone()['total_deposits'] or 0
        
        cursor.execute("SELECT SUM(referral_count) as total_referrals FROM users")
        total_referrals = cursor.fetchone()['total_referrals'] or 0
        
        conn.close()
        
        stats_msg = "📊 إحصائيات البوت:\n\n"
        stats_msg += f"👥 إجمالي المستخدمين: {total_users}\n"
        stats_msg += f"💰 إجمالي الرصيد: {total_balance:.2f} USDT\n"
        stats_msg += f"💎 إجمالي الأرباح: {total_earnings:.2f} USDT\n"
        stats_msg += f"💳 إجمالي الإيداعات: {total_deposits:.2f} USDT\n"
        stats_msg += f"👥 إجمالي الإحالات: {total_referrals}"
        
        bot.send_message(message.chat.id, stats_msg)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setvip'])
def handle_setvip(message):
    """💎 تعيين مستوى VIP - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /setvip [user_id] [level]")
            return
        
        target_user_id = parts[1]
        vip_level = int(parts[2])
        
        if vip_level not in VIP_LEVELS:
            bot.send_message(message.chat.id, "❌ مستوى VIP غير صحيح! استخدم الأرقام من 0 إلى 4")
            return
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        vip_info = VIP_LEVELS[vip_level]
        success = update_user(target_user_id, vip_level=vip_level)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين مستوى VIP للمستخدم {target_user_id} إلى {vip_info['name']}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين مستوى VIP!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

# ======================
# 🎯 معالجة الرسائل العادية
# ======================

@bot.message_handler(commands=['start', 'profile', 'الملف'])
def handle_start(message):
    user_info = f"{message.from_user.first_name} (ID: {message.from_user.id})"
    print(f"📩 استلام /start من {user_info}")
    
    try:
        profile_text = get_user_profile(
            message.from_user.id,
            message.from_user.first_name,
            message.from_user.username or ""
        )
        
        # إضافة أزرار للأوامر
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('📊 الملف الشخصي', '💰 المكافأة اليومية')
        markup.row('👥 الإحالات', '🎯 المحاولات')
        
        bot.send_message(
            message.chat.id, 
            profile_text, 
            parse_mode='Markdown',
            reply_markup=markup
        )
        print(f"✅ تم الرد على {user_info}")
        
    except Exception as e:
        print(f"❌ فشل في معالجة /start: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ، يرجى المحاولة لاحقاً")

@bot.message_handler(commands=['mining', 'mine', 'مكافأة', 'daily'])
def handle_mining(message):
    try:
        success, result_msg = claim_daily_bonus(message.from_user.id)
        bot.send_message(message.chat.id, result_msg)
        
        if success:
            # إظهار الملف الشخصي المحدث
            profile_text = get_user_profile(
                message.from_user.id,
                message.from_user.first_name,
                message.from_user.username or ""
            )
            bot.send_message(message.chat.id, profile_text, parse_mode='Markdown')
            
    except Exception as e:
        print(f"❌ خطأ في /mining: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ في استلام المكافأة")

@bot.message_handler(commands=['referral', 'invite', 'إحالات'])
def handle_referral(message):
    try:
        bot_name = bot.get_me().username
        referral_link = f"https://t.me/{bot_name}?start=ref{message.from_user.id}"
        
        referral_msg = "👥 **نظام الإحالات**\n\n"
        referral_msg += f"🔗 رابط الإحالة الخاص بك:\n`{referral_link}`\n\n"
        referral_msg += "🎁 **المكافآت:**\n"
        referral_msg += "• لكل 10 إحالات: ترقية VIP + مكافآت\n"
        referral_msg += "• إحالة جديدة: 1 USDT + محاولة إضافية\n\n"
        referral_msg += "📊 استخدم /profile لمشاهدة إحصائياتك"
        
        bot.send_message(message.chat.id, referral_msg, parse_mode='Markdown')
        
    except Exception as e:
        print(f"❌ خطأ في /referral: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ في عرض نظام الإحالات")

@bot.message_handler(commands=['attempts', 'play', 'محاولات'])
def handle_attempts(message):
    try:
        user = get_user(message.from_user.id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود")
            return
        
        vip_info = VIP_LEVELS[user['vip_level']]
        
        attempts_msg = "🎯 **نظام المحاولات**\n\n"
        attempts_msg += f"• المحاولات المتبقية: **{user['attempts']}**\n"
        attempts_msg += f"• المحاولات الأساسية: {vip_info['max_attempts']}\n"
        attempts_msg += f"• المحاولات الإضافية: {max(0, user['attempts'] - vip_info['max_attempts'])}\n\n"
        attempts_msg += f"💰 **الأرباح المحتملة:**\n"
        attempts_msg += f"• لكل محاولة: 0.1 - 1.0 USDT\n"
        attempts_msg += f"• الحد الأقصى اليومي: {vip_info['max_attempts']} USDT\n\n"
        attempts_msg += "🎮 استخدم /play للبدء في اللعب!"
        
        bot.send_message(message.chat.id, attempts_msg, parse_mode='Markdown')
        
    except Exception as e:
        print(f"❌ خطأ في /attempts: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ في عرض المحاولات")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if message.text.startswith('/'):
        return
        
    user_info = f"{message.from_user.first_name} (ID: {message.from_user.id})"
    print(f"📩 رسالة عادية من {user_info}: {message.text}")
    
    try:
        # تحديث النشاط
        update_user(
            message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username or "",
            last_activity=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        # معالجة النصوص الخاصة
        if message.text == '📊 الملف الشخصي':
            profile_text = get_user_profile(
                message.from_user.id,
                message.from_user.first_name,
                message.from_user.username or ""
            )
            bot.send_message(message.chat.id, profile_text, parse_mode='Markdown')
            
        elif message.text == '💰 المكافأة اليومية':
            success, result_msg = claim_daily_bonus(message.from_user.id)
            bot.send_message(message.chat.id, result_msg)
            
        elif message.text == '👥 الإحالات':
            handle_referral(message)
            
        elif message.text == '🎯 المحاولات':
            handle_attempts(message)
            
        else:
            bot.send_message(message.chat.id, "💬 استخدم الأزرار أدناه للتنقل بين الميزات!")
            
    except Exception as e:
        print(f"❌ فشل في معالجة الرسالة: {e}")

# ======================
# 🔧 استمرارية البوت
# ======================

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 البوت شغال! أرسل /start للبوت"

@app.route('/health')
def health():
    return "✅ OK", 200

def run_bot():
    print("🚀 جاري تشغيل البوت...")
    
    # تهيئة قاعدة البيانات
    if not init_database():
        print("⚠️  تم المتابعة بدون قاعدة البيانات")
    
    try:
        bot.polling(
            none_stop=True,
            timeout=30,
            long_polling_timeout=20
        )
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
        print("🔄 إعادة المحاولة بعد 10 ثواني...")
        time.sleep(10)
        run_bot()

if __name__ == "__main__":
    print("🎯 بدء التشغيل...")
    run_bot()
