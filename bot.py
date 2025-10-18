import os
import telebot
import random
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import time
from flask import Flask, request
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# ✅ تفعيل السجلات المفصلة
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 50)
print("🚀 نظام Webhook المحسن")
print("🔍 بدء تشغيل البوت...")
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

ADMIN_IDS = [8400225549]  # قائمة IDs المشرفين كأرقام

def is_admin(user_id):
    """التحقق إذا المستخدم مشرف"""
    return user_id in ADMIN_IDS

# ======================
# 🗄️ نظام SQLite المؤقت (للتشغيل الفوري)
# ======================

import sqlite3

DB_FILE = '/tmp/usdt_bot.db'
db_lock = threading.Lock()

# 🧩 مستويات VIP
VIP_LEVELS = {
    0: {"name": "🟢 مبتدئ", "daily_bonus": 0.8, "max_attempts": 3, "price": 0},
    1: {"name": "🟢 برونز", "daily_bonus": 1.25, "max_attempts": 5, "price": 5},
    2: {"name": "🔵 سيلفر", "daily_bonus": 1.75, "max_attempts": 8, "price": 10},
    3: {"name": "🟡 جولد", "daily_bonus": 2.75, "max_attempts": 13, "price": 20}
}

# 🧩 كاش للذاكرة
user_cache = {}
CACHE_TIMEOUT = 300

def init_database():
    """تهيئة قاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0.75,
                referral_count INTEGER DEFAULT 0,
                new_referrals INTEGER DEFAULT 0,
                vip_level INTEGER DEFAULT 0,
                attempts INTEGER DEFAULT 3,
                total_earnings REAL DEFAULT 0.75,
                total_deposits REAL DEFAULT 0.0,
                registration_date TEXT,
                last_activity TEXT,
                last_mining_date TEXT,
                withdrawal_address TEXT,
                games_played_today INTEGER DEFAULT 0,
                last_reset_date TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ تم تهيئة قاعدة البيانات بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        return False

def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ فشل في الاتصال بقاعدة البيانات: {e}")
        return None

def get_user(user_id):
    """جلب أو إنشاء مستخدم"""
    user_id_str = str(user_id)
    
    with db_lock:
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                return create_default_user(user_id_str)
                
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id_str,))
            user_data = cursor.fetchone()
            
            if user_data:
                user_dict = dict(user_data)
                
                # التحقق من إعادة تعيين المحاولات اليومية
                today = datetime.now().strftime('%Y-%m-%d')
                if user_dict.get('last_reset_date') != today:
                    user_dict['games_played_today'] = 0
                    user_dict['last_reset_date'] = today
                    save_user(user_dict)
                
                return user_dict
            else:
                return create_default_user(user_id_str)
                
        except Exception as e:
            print(f"❌ خطأ في جلب بيانات المستخدم {user_id}: {e}")
            return create_default_user(user_id_str)
        finally:
            if conn:
                conn.close()

def create_default_user(user_id):
    """إنشاء مستخدم جديد"""
    user_data = {
        'user_id': user_id,
        'username': "",
        'first_name': "",
        'balance': 0.75,
        'referral_count': 0,
        'new_referrals': 0,
        'vip_level': 0,
        'attempts': 3,
        'total_earnings': 0.75,
        'total_deposits': 0.0,
        'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_activity': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_mining_date': None,
        'withdrawal_address': "",
        'games_played_today': 0,
        'last_reset_date': datetime.now().strftime('%Y-%m-%d')
    }
    
    save_user(user_data)
    return user_data

def save_user(user_data):
    """حفظ بيانات المستخدم"""
    with db_lock:
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO users (
                    user_id, username, first_name, balance, referral_count, new_referrals,
                    vip_level, attempts, total_earnings, total_deposits, registration_date,
                    last_activity, last_mining_date, withdrawal_address, games_played_today,
                    last_reset_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_data['user_id'], user_data['username'], user_data['first_name'],
                user_data['balance'], user_data['referral_count'], user_data['new_referrals'],
                user_data['vip_level'], user_data['attempts'], user_data['total_earnings'],
                user_data['total_deposits'], user_data['registration_date'],
                user_data['last_activity'], user_data['last_mining_date'],
                user_data['withdrawal_address'], user_data['games_played_today'],
                user_data['last_reset_date']
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ خطأ في حفظ بيانات المستخدم: {e}")
            return False
        finally:
            if conn:
                conn.close()

def update_user(user_id, **kwargs):
    """تحديث بيانات المستخدم"""
    user = get_user(user_id)
    if not user:
        return False
    
    for key, value in kwargs.items():
        user[key] = value
    
    user['last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return save_user(user)

# ======================
# 🧮 دوال المساعدة
# ======================

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
    
    reg_date = datetime.strptime(user['registration_date'].split()[0], '%Y-%m-%d')
    now = datetime.now()
    days = (now - reg_date).days
    return max(0, days)

def get_remaining_attempts(user):
    """حساب المحاولات المتبقية"""
    base_attempts = VIP_LEVELS[user['vip_level']]['max_attempts']
    extra_attempts = user.get('new_referrals', 0)
    used_attempts = user.get('games_played_today', 0)
    total_attempts = base_attempts + extra_attempts
    remaining = total_attempts - used_attempts
    return max(0, remaining), total_attempts, extra_attempts

def can_withdraw(user):
    """التحقق من إمكانية السحب"""
    has_10_days = get_days_since_registration(user['user_id']) >= 10
    has_150_balance = user['balance'] >= 150
    has_address = bool(user.get('withdrawal_address', ''))
    has_15_refs = user.get('new_referrals', 0) >= 15
    
    return has_10_days and has_150_balance and has_address and has_15_refs

def get_user_profile(user_id, first_name="", username=""):
    """إنشاء نص الملف الشخصي"""
    user = get_user(user_id)
    if not user:
        return "❌ المستخدم غير موجود"
    
    update_user(
        user_id,
        first_name=first_name,
        username=username or "",
        last_activity=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
    vip_info = VIP_LEVELS[user['vip_level']]
    mining_time = get_mining_time_left(user_id)
    days_registered = get_days_since_registration(user_id)
    
    profile = f"📊 **الملف الشخصي**\n\n"
    profile += f"👤 المستخدم: {user['first_name'] or 'غير معروف'}\n"
    profile += f"🆔 المعرف: {user['user_id']}\n"
    profile += f"💰 الرصيد: **{user['balance']:.2f} USDT**\n"
    profile += f"👥 الإحالات: **{user['referral_count']} مستخدم**\n"
    profile += f"📈 الإحالات الجديدة: **{user['new_referrals']}/15**\n"
    profile += f"🏆 مستوى VIP: {vip_info['name']}\n"
    profile += f"🎯 المحاولات المتبقية: **{remaining_attempts}** ({total_attempts} أساسية + {extra_attempts} إضافية)\n"
    profile += f"📅 أيام التسجيل: **{days_registered} يوم**\n\n"
    
    profile += f"⏰ مكافأة التعدين: {mining_time}\n\n"
    
    profile += f"💎 إجمالي الأرباح: **{user['total_earnings']:.2f} USDT**\n"
    profile += f"💳 إجمالي الإيداعات: **{user['total_deposits']:.2f} USDT**\n"
    profile += f"📅 تاريخ التسجيل: {user['registration_date'].split()[0]}"
    
    return profile

# ======================
# 🎯 الواجهة الرئيسية
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
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎮 الألعاب", callback_data="games"),
            InlineKeyboardButton("💎 خدمات VIP", callback_data="vip_services"),
            InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral"),
            InlineKeyboardButton("💰 السحب", callback_data="withdraw")
        )
        keyboard.add(
            InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4")
        )
        
        bot.send_message(
            message.chat.id, 
            profile_text, 
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        print(f"✅ تم الرد على {user_info}")
        
    except Exception as e:
        print(f"❌ فشل في معالجة /start: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ، يرجى المحاولة لاحقاً")

@bot.message_handler(commands=['myid'])
def handle_myid(message):
    """عرض الـ ID الخاص بالمستخدم"""
    try:
        bot.reply_to(message, f"🆔 معرفك: `{message.from_user.id}`", parse_mode='Markdown')
    except Exception as e:
        print(f"❌ خطأ في /myid: {e}")

# 🎮 قائمة الألعاب
@bot.callback_query_handler(func=lambda call: call.data == "games")
def show_games(call):
    try:
        user = get_user(call.from_user.id)
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
        
        games_text = f"""🎮 قائمة الألعاب

المحاولات المتبقية: {remaining_attempts}/{total_attempts}
🎰 الربح لكل محاولة: 2.5 USDT

اختر اللعبة:"""
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎰 سلوت", callback_data="game_slot"),
            InlineKeyboardButton("🎲 نرد", callback_data="game_dice")
        )
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        
        bot.edit_message_text(games_text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ خطأ في show_games: {e}")

# 🎰 لعبة السلوت
@bot.callback_query_handler(func=lambda call: call.data == "game_slot")
def play_slot(call):
    try:
        user = get_user(call.from_user.id)
        remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
        
        if remaining_attempts <= 0:
            bot.answer_callback_query(call.id, "❌ لا توجد محاولات متبقية اليوم!", show_alert=True)
            return
        
        user['games_played_today'] = user.get('games_played_today', 0) + 1
        save_user(user)
        
        symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎"]
        result = [random.choice(symbols) for _ in range(3)]
        
        if result[0] == result[1] == result[2]:
            win_amount = 2.5
            win_text = "🎉 ربح كبير!"
        elif result[0] == result[1] or result[1] == result[2]:
            win_amount = 1.25
            win_text = "👍 ربح جيد!"
        else:
            win_amount = 0
            win_text = "😞 حاول مرة أخرى"
        
        user['balance'] += win_amount
        if win_amount > 0:
            user['total_earnings'] += win_amount
        
        save_user(user)
        remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
        
        game_result = f"""🎰 لعبة السلوت

{' | '.join(result)}

{win_text}
💰 الربح: {win_amount:.2f} USDT

🎯 المحاولات المتبقية: {remaining_attempts}/{total_attempts}"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🎰 العب مرة أخرى", callback_data="game_slot"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع للألعاب", callback_data="games"))
        
        bot.edit_message_text(game_result, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ خطأ في play_slot: {e}")

# 🎲 لعبة النرد
@bot.callback_query_handler(func=lambda call: call.data == "game_dice")
def play_dice(call):
    try:
        user = get_user(call.from_user.id)
        remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
        
        if remaining_attempts <= 0:
            bot.answer_callback_query(call.id, "❌ لا توجد محاولات متبقية اليوم!", show_alert=True)
            return
        
        user['games_played_today'] = user.get('games_played_today', 0) + 1
        save_user(user)
        
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        if total == 7:
            win_amount = 2.5
            win_text = "🎉 ربح كبير! (رقم الحظ)"
        elif total >= 10:
            win_amount = 1.5
            win_text = "👍 ربح جيد!"
        elif total <= 4:
            win_amount = 1.0
            win_text = "👌 ربح صغير"
        else:
            win_amount = 0
            win_text = "😞 حاول مرة أخرى"
        
        user['balance'] += win_amount
        if win_amount > 0:
            user['total_earnings'] += win_amount
        
        save_user(user)
        remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
        
        game_result = f"""🎲 لعبة النرد

🎲 النرد: {dice1} + {dice2} = {total}

{win_text}
💰 الربح: {win_amount:.2f} USDT

🎯 المحاولات المتبقية: {remaining_attempts}/{total_attempts}"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🎲 العب مرة أخرى", callback_data="game_dice"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع للألعاب", callback_data="games"))
        
        bot.edit_message_text(game_result, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ خطأ في play_dice: {e}")

# 💎 خدمات VIP
@bot.callback_query_handler(func=lambda call: call.data == "vip_services")
def show_vip_services(call):
    try:
        vip_text = """💎 العضويات VIP المميزة:

🟢 برونز VIP - 5 USDT:
• مكافأة يومية 1.25 USDT
• +2 محاولات ألعاب يومية
• دعم فني متميز

🔵 سيلفر VIP - 10 USDT:
• مكافأة يومية 1.75 USDT  
• +5 محاولات ألعاب يومية
• أولوية في معالجة طلبات السحب

🟡 جولد VIP - 20 USDT:
• مكافأة يومية 2.75 USDT
• +10 محاولات ألعاب يومية
• أولوية قصوى في جميع الخدمات

اختر العضوية المناسبة:"""
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("🟢 شراء برونز VIP - 5 USDT", callback_data="buy_bronze"),
            InlineKeyboardButton("🔵 شراء سيلفر VIP - 10 USDT", callback_data="buy_silver"),
            InlineKeyboardButton("🟡 شراء جولد VIP - 20 USDT", callback_data="buy_gold"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile")
        )
        
        bot.edit_message_text(vip_text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ خطأ في show_vip_services: {e}")

# شراء VIP
@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_vip_purchase(call):
    try:
        user = get_user(call.from_user.id)
        vip_type = call.data.replace('buy_', '')
        
        vip_names = {
            'bronze': '🟢 برونز VIP',
            'silver': '🔵 سيلفر VIP', 
            'gold': '🟡 جولد VIP'
        }
        
        vip_prices = {
            'bronze': 5.0,
            'silver': 10.0,
            'gold': 20.0
        }
        
        vip_name = vip_names.get(vip_type, 'VIP')
        vip_price = vip_prices.get(vip_type, 0)
        
        request_text = f"""🛒 طلب شراء جديد:

👤 المستخدم: {user['first_name']} 
🆔 الآيدي: {call.from_user.id}
📞 للتواصل: [اضغط هنا](tg://user?id={call.from_user.id})
💎 النوع: {vip_name}
💰 السعر: {vip_price} USDT
💰 الرصيد الحالي: {user['balance']:.1f} USDT
📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, request_text, parse_mode='Markdown')
            except Exception as e:
                print(f"❌ Failed to send to admin {admin_id}: {e}")
        
        bot.answer_callback_query(
            call.id, 
            f"✅ تم إرسال طلب شراء {vip_name} للإدارة", 
            show_alert=True
        )
    except Exception as e:
        print(f"❌ خطأ في handle_vip_purchase: {e}")

# 🎯 رابط الاحالات
@bot.callback_query_handler(func=lambda call: call.data == "referral")
def handle_referral(call):
    try:
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start=ref{call.from_user.id}"
        
        referral_text = f"""🎯 نظام الإحالات

🔗 رابط الدعوة الخاص بك:
`{referral_link}`

👥 مزايا الإحالات:
• 🎁 1 USDT مكافأة فورية لكل إحالة
• +1 محاولة ألعاب يومية لكل إحالة  
• فرصة ربح مضاعفة
• وصول أسرع لشروط السحب

📤 شارك الرابط مع أصدقائك واكسب المزيد!"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={referral_link}&text=انضم%20إلي%20في%20هذا%20البوت%20الرائع%20واربح%20USDT%20مجاناً!"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        
        bot.edit_message_text(
            referral_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"❌ خطأ في handle_referral: {e}")

# 💰 نظام السحب
@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def handle_withdraw(call):
    try:
        user = get_user(call.from_user.id)
        
        if not can_withdraw(user):
            days = get_days_since_registration(call.from_user.id)
            if days < 10:
                error_msg = f"❌ تحتاج إلى 10 أيام تسجيل على الأقل للسحب\n📅 أيامك الحالية: {days} يوم"
            elif user['balance'] < 150:
                error_msg = f"❌ الحد الأدنى للسحب هو 150 USDT\n💰 رصيدك الحالي: {user['balance']:.1f} USDT"
            elif not user.get('withdrawal_address'):
                error_msg = "❌ يرجى إعداد عنوان المحفظة أولاً"
            elif user.get('new_referrals', 0) < 15:
                error_msg = f"❌ تحتاج إلى 15 إحالة جديدة على الأقل للسحب\n👥 إحالاتك الجديدة: {user.get('new_referrals', 0)}/15"
            else:
                error_msg = "❌ لا يمكن السحب حالياً، يرجى المحاولة لاحقاً"
            
            bot.answer_callback_query(call.id, error_msg, show_alert=True)
            return
        
        show_withdrawal_options(call.message, user)
    except Exception as e:
        print(f"❌ خطأ في handle_withdraw: {e}")

def show_withdrawal_options(message, user):
    try:
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("💰 سحب 150 USDT", callback_data="withdraw_150"),
            InlineKeyboardButton("💰 سحب 300 USDT", callback_data="withdraw_300"),
            InlineKeyboardButton("💰 سحب 500 USDT", callback_data="withdraw_500"),
            InlineKeyboardButton("💰 سحب كل الرصيد", callback_data="withdraw_all")
        )
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        
        if not user.get('withdrawal_address'):
            msg = bot.send_message(
                message.chat.id,
                "💰 نظام السحب\n\n"
                "📝 الرجاء إرسال عنوان محفظة USDT (TRC20):"
            )
            bot.register_next_step_handler(msg, process_withdrawal_address, user)
            return
        
        bot.send_message(
            message.chat.id,
            f"💰 نظام السحب\n\n"
            f"💳 عنوان المحفظة: {user['withdrawal_address']}\n"
            f"💰 الرصيد المتاح: {user['balance']:.1f} USDT\n"
            f"📅 أيام التسجيل: {get_days_since_registration(user['user_id'])}/10 يوم\n"
            f"👥 الإحالات الجديدة: {user.get('new_referrals', 0)}/15\n\n"
            f"اختر مبلغ السحب:",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ خطأ في show_withdrawal_options: {e}")

def process_withdrawal_address(message, user):
    try:
        address = message.text.strip()
        if len(address) < 10:
            msg = bot.send_message(
                message.chat.id,
                "❌ عنوان غير صحيح! الرجاء إرسال عنوان محفظة USDT (TRC20) صحيح:"
            )
            bot.register_next_step_handler(msg, process_withdrawal_address, user)
            return
        
        user['withdrawal_address'] = address
        save_user(user)
        show_withdrawal_options(message, user)
    except Exception as e:
        print(f"❌ خطأ في process_withdrawal_address: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_'))
def process_withdrawal(call):
    try:
        user = get_user(call.from_user.id)
        withdraw_type = call.data.replace('withdraw_', '')
        
        if withdraw_type == '150':
            amount = 150.0
        elif withdraw_type == '300':
            amount = 300.0
        elif withdraw_type == '500':
            amount = 500.0
        else:
            amount = user['balance']
        
        if user['balance'] < amount:
            bot.answer_callback_query(call.id, f"❌ رصيدك غير كافي! الرصيد: {user['balance']:.1f} USDT", show_alert=True)
            return
        
        if amount < 150:
            bot.answer_callback_query(call.id, "❌ الحد الأدنى للسحب هو 150 USDT", show_alert=True)
            return
        
        if get_days_since_registration(call.from_user.id) < 10:
            bot.answer_callback_query(call.id, f"❌ تحتاج إلى 10 أيام تسجيل للسحب\n📅 أيامك: {get_days_since_registration(call.from_user.id)}", show_alert=True)
            return
        
        if user.get('new_referrals', 0) < 15:
            bot.answer_callback_query(call.id, f"❌ تحتاج إلى 15 إحالة جديدة للسحب\n👥 إحالاتك: {user.get('new_referrals', 0)}/15", show_alert=True)
            return
        
        user['balance'] -= amount
        save_user(user)
        
        withdraw_text = f"""🏦 طلب سحب جديد:

👤 المستخدم: {user['first_name']} 
🆔 الآيدي: {call.from_user.id}
📞 للتواصل: [اضغط هنا](tg://user?id={call.from_user.id})
💳 عنوان المحفظة: {user['withdrawal_address']}
💰 المبلغ: {amount:.1f} USDT
📊 الرصيد المتبقي: {user['balance']:.1f} USDT
📅 أيام التسجيل: {get_days_since_registration(call.from_user.id)} يوم
👥 الإحالات الجديدة: {user.get('new_referrals', 0)}/15
📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, withdraw_text, parse_mode='Markdown')
            except Exception as e:
                print(f"❌ Failed to send to admin {admin_id}: {e}")
        
        bot.answer_callback_query(
            call.id, 
            f"✅ تم إرسال طلب سحب {amount:.1f} USDT للإدارة", 
            show_alert=True
        )
    except Exception as e:
        print(f"❌ خطأ في process_withdrawal: {e}")

# 🔙 رجوع للبروفايل
@bot.callback_query_handler(func=lambda call: call.data == "back_to_profile")
def back_to_profile(call):
    try:
        user = get_user(call.from_user.id)
        profile_text = get_user_profile(
            call.from_user.id,
            call.from_user.first_name,
            call.from_user.username or ""
        )
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎮 الألعاب", callback_data="games"),
            InlineKeyboardButton("💎 خدمات VIP", callback_data="vip_services"),
            InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral"),
            InlineKeyboardButton("💰 السحب", callback_data="withdraw")
        )
        keyboard.add(
            InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4")
        )
        
        bot.edit_message_text(
            profile_text, 
            call.message.chat.id, 
            call.message.message_id, 
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"❌ خطأ في back_to_profile: {e}")

# معالجة الإحالات من رابط الدعوة
@bot.message_handler(func=lambda message: message.text and message.text.startswith('/start ref'))
def handle_referral_start(message):
    try:
        referrer_id = message.text.split('ref')[-1]
        
        new_user = get_user(message.from_user.id)
        new_user['first_name'] = message.from_user.first_name or "مستخدم"
        new_user['username'] = message.from_user.username or ""
        save_user(new_user)
        
        if referrer_id.isdigit():
            referrer = get_user(int(referrer_id))
            if referrer and referrer['user_id'] != new_user['user_id']:
                referrer['balance'] += 1.0
                referrer['total_earnings'] += 1.0
                referrer['referral_count'] += 1
                referrer['new_referrals'] += 1
                
                save_user(referrer)
                
                try:
                    bot.send_message(
                        int(referrer_id),
                        f"🎉 تهانينا! لقد قام {new_user['first_name']} بالتسجيل من خلال رابطك!\n"
                        f"🎁 تم إضافة 1 USDT إلى رصيدك!\n"
                        f"💰 رصيدك الجديد: {referrer['balance']:.1f} USDT"
                    )
                except:
                    pass
        
        handle_start(message)
    except Exception as e:
        print(f"❌ خطأ في handle_referral_start: {e}")

# ======================
# 🛠️ الأوامر الإدارية
# ======================

@bot.message_handler(commands=['quickadd'])
def handle_quickadd(message):
    """💰 إضافة رصيد - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
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

# ... (بقية الأوامر الإدارية - نفس الكود السابق)
# للحفاظ على الإجابة قصيرة، حأترك بقية الأوامر الإدارية كما هي

# ======================
# 🔧 نظام Webhook الجديد
# ======================

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 البوت شغال! أرسل /start في تيليجرام"

@app.route('/health')
def health():
    return "✅ OK", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook لاستقبال التحديثات من تيليجرام"""
    if request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return 'OK', 200
        except Exception as e:
            print(f"❌ خطأ في معالجة webhook: {e}")
            return 'Error', 500
    return 'Forbidden', 403

def set_webhook():
    """إعداد webhook على تيليجرام"""
    try:
        # الحصول على دومين Railway تلقائياً
        railway_url = os.environ.get('RAILWAY_STATIC_URL')
        if not railway_url:
            print("❌ RAILWAY_STATIC_URL غير موجود")
            return False
        
        webhook_url = f"https://{railway_url}/webhook"
        print(f"🔄 جاري إعداد webhook على: {webhook_url}")
        
        # إزالة أي webhook سابق
        bot.remove_webhook()
        time.sleep(1)
        
        # تعيين webhook جديد
        result = bot.set_webhook(url=webhook_url)
        if result:
            print(f"✅ تم تعيين webhook بنجاح: {webhook_url}")
            return True
        else:
            print("❌ فشل في تعيين webhook")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في إعداد webhook: {e}")
        return False

def run_bot():
    """تشغيل البوت مع Webhook"""
    print("🚀 جاري تشغيل البوت بنظام Webhook...")
    
    # تهيئة قاعدة البيانات
    if not init_database():
        print("⚠️  تم المتابعة بدون قاعدة البيانات")
    
    # إعداد webhook
    if set_webhook():
        print("🎉 البوت جاهز للاستقبال عبر Webhook!")
    else:
        print("❌ فشل في إعداد Webhook، جاري استخدام Polling كبديل...")
        try:
            bot.polling(none_stop=True, timeout=30)
        except Exception as e:
            print(f"❌ خطأ في Polling: {e}")

if __name__ == "__main__":
    print("🎯 بدء التشغيل بنظام Webhook...")
    run_bot()
