import os
import telebot
import sqlite3
import random
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import time
import requests
from flask import Flask
import logging
import sys

# ✅ تمكين السجلات المفصلة
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# 📡 Flask Server for Railway
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 USDT Telegram Bot is Running!"

@app.route('/health')
def health_check():
    return "✅ OK", 200

@app.route('/ping')
def ping():
    return "🏓 PONG", 200

# 🔧 الإعدادات من environment variables
print("🔍 جاري تحميل الإعدادات...")
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7973697789:AAFXfYXTgYaTAF1j7IGhp2kiv-kxrN1uImk')

if not BOT_TOKEN:
    print("❌ خطأ: BOT_TOKEN غير موجود في environment variables!")
    print("💡 الرجاء إضافة BOT_TOKEN في إعدادات Railway")
    exit(1)

print(f"✅ تم تحميل BOT_TOKEN: {BOT_TOKEN[:10]}...")

ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_ID', '8400225549').split(',')]

print("🤖 جاري إنشاء البوت...")
bot = telebot.TeleBot(BOT_TOKEN)
print("✅ تم إنشاء البوت بنجاح!")

# ======================
# 🗄️ نظام قاعدة البيانات SQLite
# ======================

DB_FILE = 'usdt_bot.db'
db_lock = threading.Lock()

def init_database():
    """تهيئة قاعدة البيانات"""
    with db_lock:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance REAL DEFAULT 0.75,
                    referrals_count INTEGER DEFAULT 0,
                    referrals_new INTEGER DEFAULT 0,
                    games_played_today INTEGER DEFAULT 0,
                    total_games_played INTEGER DEFAULT 0,
                    total_earned REAL DEFAULT 0.75,
                    total_deposits REAL DEFAULT 0.0,
                    vip_level INTEGER DEFAULT 0,
                    registration_date TEXT,
                    last_activity TEXT,
                    last_reset_date TEXT,
                    withdrawal_address TEXT,
                    registration_days INTEGER DEFAULT 0,
                    last_daily_check TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            print("✅ تم تهيئة قاعدة البيانات SQLite بنجاح!")
            return True
        except Exception as e:
            print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
            return False

def get_user(user_id):
    """جلب بيانات المستخدم"""
    with db_lock:
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
            user_data = cursor.fetchone()
            
            if user_data:
                user_dict = dict(user_data)
                
                # التحقق من إعادة تعيين المحاولات اليومية
                last_reset = user_dict.get('last_reset_date', '2000-01-01')
                today = datetime.now().strftime('%Y-%m-%d')
                
                if last_reset != today:
                    user_dict['games_played_today'] = 0
                    user_dict['last_reset_date'] = today
                    
                    # منح المكافأة اليومية
                    daily_bonus = 0.75
                    user_dict['balance'] += daily_bonus
                    user_dict['total_earned'] += daily_bonus
                    
                    # منح مكافأة VIP
                    vip_bonus = {1: 0.5, 2: 1.0, 3: 2.0}
                    if user_dict['vip_level'] in vip_bonus:
                        bonus = vip_bonus[user_dict['vip_level']]
                        user_dict['balance'] += bonus
                        user_dict['total_earned'] += bonus
                    
                    # تحديث البيانات
                    save_user(user_dict)
                
                conn.close()
                return user_dict
            else:
                conn.close()
                return create_default_user(user_id)
                
        except Exception as e:
            print(f"❌ خطأ في جلب بيانات المستخدم {user_id}: {e}")
            return create_default_user(user_id)

def create_default_user(user_id):
    """إنشاء مستخدم جديد بإعدادات افتراضية"""
    user_data = {
        'user_id': str(user_id),
        'username': "",
        'first_name': "",
        'balance': 0.75,
        'referrals_count': 0,
        'referrals_new': 0,
        'games_played_today': 0,
        'total_games_played': 0,
        'total_earned': 0.75,
        'total_deposits': 0.0,
        'vip_level': 0,
        'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_activity': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_reset_date': datetime.now().strftime('%Y-%m-%d'),
        'withdrawal_address': "",
        'registration_days': 0,
        'last_daily_check': datetime.now().strftime('%Y-%m-%d')
    }
    
    save_user(user_data)
    return user_data

def save_user(user_data):
    """حفظ بيانات المستخدم"""
    with db_lock:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO users (
                    user_id, username, first_name, balance, referrals_count, referrals_new,
                    games_played_today, total_games_played, total_earned, total_deposits,
                    vip_level, registration_date, last_activity, last_reset_date,
                    withdrawal_address, registration_days, last_daily_check
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_data['user_id'], user_data['username'], user_data['first_name'],
                user_data['balance'], user_data['referrals_count'], user_data['referrals_new'],
                user_data['games_played_today'], user_data['total_games_played'],
                user_data['total_earned'], user_data['total_deposits'], user_data['vip_level'],
                user_data['registration_date'], user_data['last_activity'],
                user_data['last_reset_date'], user_data['withdrawal_address'],
                user_data['registration_days'], user_data['last_daily_check']
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ خطأ في حفظ بيانات المستخدم {user_data['user_id']}: {e}")
            return False

def update_user_activity(user_id):
    """تحديث نشاط المستخدم"""
    user = get_user(user_id)
    user['last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # حساب أيام التسجيل
    registration_date = datetime.strptime(user['registration_date'].split()[0], '%Y-%m-%d')
    current_date = datetime.now()
    days_registered = (current_date - registration_date).days
    user['registration_days'] = days_registered
    
    save_user(user)

def get_vip_level_name(level):
    """تحويل مستوى VIP إلى اسم"""
    vip_names = {
        0: "🟢 مبتدئ",
        1: "🟢 برونز", 
        2: "🔵 سيلفر",
        3: "🟡 جولد"
    }
    return vip_names.get(level, "🟢 مبتدئ")

def get_remaining_attempts(user):
    """حساب المحاولات المتبقية"""
    base_attempts = 3
    extra_attempts = user.get('referrals_new', 0)
    used_attempts = user.get('games_played_today', 0)
    total_attempts = base_attempts + extra_attempts
    remaining = total_attempts - used_attempts
    return max(0, remaining), total_attempts, extra_attempts

def get_mining_reward_time():
    """وقت مكافأة التعدين"""
    now = datetime.now()
    next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    time_left = next_reset - now
    
    hours = int(time_left.total_seconds() // 3600)
    minutes = int((time_left.total_seconds() % 3600) // 60)
    
    return f"{hours:02d}س {minutes:02d}د ⏳"

def can_withdraw(user):
    """التحقق من إمكانية السحب"""
    has_10_days = user.get('registration_days', 0) >= 10
    has_150_balance = user['balance'] >= 150
    has_address = bool(user.get('withdrawal_address', ''))
    has_15_new_refs = user.get('referrals_new', 0) >= 15
    
    return has_10_days and has_150_balance and has_address and has_15_new_refs

# 🎯 الواجهة الرئيسية
@bot.message_handler(commands=['start', 'profile'])
def start_command(message):
    try:
        user = get_user(message.from_user.id)
        user['first_name'] = message.from_user.first_name or "مستخدم"
        user['username'] = message.from_user.username or ""
        update_user_activity(message.from_user.id)
        
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
        vip_name = get_vip_level_name(user['vip_level'])
        mining_time = get_mining_reward_time()
        
        user_name = message.from_user.first_name or "مستخدم"
        
        profile_text = f"""📊 الملف الشخصي

👤 المستخدم: {user_name}
🆔 المعرف: {message.from_user.id}
💰 الرصيد: {user['balance']:.1f} USDT
👥 الإحالات: {user['referrals_count']} مستخدم
📈 الإحالات الجديدة: {user.get('referrals_new', 0)}/{user['referrals_count']}
🏆 مستوى VIP: {vip_name}
🎯 المحاولات المتبقية: {remaining_attempts} ({total_attempts} أساسية + {extra_attempts} إضافية)
📅 أيام التسجيل: {user.get('registration_days', 0)} يوم

⏰ مكافأة التعدين: {mining_time}

💎 إجمالي الأرباح: {user['total_earned']:.1f} USDT
💳 إجمالي الإيداعات: {user['total_deposits']:.1f} USDT
📅 تاريخ التسجيل: {user['registration_date'].split()[0]}"""

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
        
        bot.send_message(message.chat.id, profile_text, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ خطأ في start_command: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")

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
        
        user['games_played_today'] += 1
        user['total_games_played'] += 1
        
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
            user['total_earned'] += win_amount
        
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
        
        user['games_played_today'] += 1
        user['total_games_played'] += 1
        
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
            user['total_earned'] += win_amount
        
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
• +10% تعدين
• مكافأة يومية 0.5 USDT
• +2 محاولات ألعاب يومية

🔵 سيلفر VIP - 10 USDT:
• +25% تعدين  
• مكافأة يومية 1.0 USDT
• +5 محاولات ألعاب يومية

🟡 جولد VIP - 20 USDT:
• +50% تعدين
• مكافأة يومية 2.0 USDT
• +10 محاولات ألعاب يومية

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

# إرسال طلبات الشراء للادمن
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
📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⏰ الرجاء التواصل مع المستخدم مباشرة بالضغط على الرابط أعلاه"""
        
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

# 💰 نظام السحب
@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def handle_withdraw(call):
    try:
        user = get_user(call.from_user.id)
        
        if not can_withdraw(user):
            if user.get('registration_days', 0) < 10:
                error_msg = f"❌ تحتاج إلى 10 أيام تسجيل على الأقل للسحب\n📅 أيامك الحالية: {user.get('registration_days', 0)} يوم"
            elif user['balance'] < 150:
                error_msg = f"❌ الحد الأدنى للسحب هو 150 USDT\n💰 رصيدك الحالي: {user['balance']:.1f} USDT"
            elif not user.get('withdrawal_address'):
                error_msg = "❌ يرجى إعداد عنوان المحفظة أولاً"
            elif user.get('referrals_new', 0) < 15:
                error_msg = f"❌ تحتاج إلى 15 إحالة جديدة على الأقل للسحب\n👥 إحالاتك الجديدة: {user.get('referrals_new', 0)}/15"
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
                "📝 الرجاء إرسال عنوان محفظتك USDT (TRC20):"
            )
            bot.register_next_step_handler(msg, process_withdrawal_address, user)
            return
        
        bot.send_message(
            message.chat.id,
            f"💰 نظام السحب\n\n"
            f"💳 عنوان المحفظة: {user['withdrawal_address']}\n"
            f"💰 الرصيد المتاح: {user['balance']:.1f} USDT\n"
            f"📅 أيام التسجيل: {user.get('registration_days', 0)}/10 يوم\n"
            f"👥 الإحالات الجديدة: {user.get('referrals_new', 0)}/15\n\n"
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
        
        if user.get('registration_days', 0) < 10:
            bot.answer_callback_query(call.id, f"❌ تحتاج إلى 10 أيام تسجيل للسحب\n📅 أيامك: {user.get('registration_days', 0)}", show_alert=True)
            return
        
        if user.get('referrals_new', 0) < 15:
            bot.answer_callback_query(call.id, f"❌ تحتاج إلى 15 إحالة جديدة للسحب\n👥 إحالاتك: {user.get('referrals_new', 0)}/15", show_alert=True)
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
📅 أيام التسجيل: {user.get('registration_days', 0)} يوم
👥 الإحالات الجديدة: {user.get('referrals_new', 0)}/15
📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ تم خصم المبلغ من رصيد المستخدم"""
        
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

# 🎯 رابط الاحالات
@bot.callback_query_handler(func=lambda call: call.data == "referral")
def handle_referral(call):
    try:
        update_user_activity(call.from_user.id)
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

# 🔙 رجوع للبروفايل
@bot.callback_query_handler(func=lambda call: call.data == "back_to_profile")
def back_to_profile(call):
    try:
        user = get_user(call.from_user.id)
        update_user_activity(call.from_user.id)
        
        user_name = call.from_user.first_name or "مستخدم"
        
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
        vip_name = get_vip_level_name(user['vip_level'])
        mining_time = get_mining_reward_time()
        
        profile_text = f"""📊 الملف الشخصي

👤 المستخدم: {user_name}
🆔 المعرف: {call.from_user.id}
💰 الرصيد: {user['balance']:.1f} USDT
👥 الإحالات: {user['referrals_count']} مستخدم
📈 الإحالات الجديدة: {user.get('referrals_new', 0)}/{user['referrals_count']}
🏆 مستوى VIP: {vip_name}
🎯 المحاولات المتبقية: {remaining_attempts} ({total_attempts} أساسية + {extra_attempts} إضافية)
📅 أيام التسجيل: {user.get('registration_days', 0)} يوم

⏰ مكافأة التعدين: {mining_time}

💎 إجمالي الأرباح: {user['total_earned']:.1f} USDT
💳 إجمالي الإيداعات: {user['total_deposits']:.1f} USDT
📅 تاريخ التسجيل: {user['registration_date'].split()[0]}"""

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
            reply_markup=keyboard
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
        
        if referrer_id.isdigit():
            referrer = get_user(int(referrer_id))
            if referrer['user_id'] != new_user['user_id']:
                referral_bonus = 1.0
                referrer['balance'] += referral_bonus
                referrer['total_earned'] += referral_bonus
                referrer['referrals_count'] += 1
                referrer['referrals_new'] += 1
                
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
        
        start_command(message)
    except Exception as e:
        print(f"❌ خطأ في handle_referral_start: {e}")

# =============================================
# ⚡ الأوامر الإدارية
# =============================================

@bot.message_handler(commands=['myid'])
def myid(message):
    try:
        update_user_activity(message.from_user.id)
        bot.reply_to(message, f"🆔 معرفك: `{message.from_user.id}`", parse_mode='Markdown')
    except Exception as e:
        print(f"❌ خطأ في myid: {e}")

@bot.message_handler(commands=['quickadd'])
def quick_add(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        update_user_activity(message.from_user.id)
        
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /quickadd [user_id] [amount]")
            return
        
        user_id = int(parts[1])
        amount = float(parts[2])
        
        user = get_user(user_id)
        user['balance'] += amount
        user['total_earned'] += amount
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم إضافة {amount} USDT للمستخدم {user_id}\n💰 الرصيد الجديد: {user['balance']:.1f} USDT")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['deposit'])
def deposit_command(message):
    """إيداع رصيد للمستخدم - أمر إداري"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /deposit [user_id] [amount]\nمثال: /deposit 123456789 50.5")
            return
        
        user_id = int(parts[1])
        amount = float(parts[2])
        
        if amount <= 0:
            bot.reply_to(message, "❌ المبلغ يجب أن يكون أكبر من الصفر!")
            return
        
        user = get_user(user_id)
        user['balance'] += amount
        user['total_deposits'] += amount
        user['total_earned'] += amount
        
        save_user(user)
        
        # إرسال إشعار للمستخدم
        try:
            bot.send_message(
                user_id,
                f"🎉 تم إيداع {amount:.1f} USDT إلى رصيدك!\n"
                f"💰 رصيدك الجديد: {user['balance']:.1f} USDT\n"
                f"💳 الإيداع من: الإدارة"
            )
        except:
            pass
        
        bot.reply_to(message, 
            f"✅ تم إيداع {amount:.1f} USDT للمستخدم {user_id}\n"
            f"👤 الاسم: {user['first_name']}\n"
            f"💰 الرصيد الجديد: {user['balance']:.1f} USDT\n"
            f"💳 إجمالي الإيداعات: {user['total_deposits']:.1f} USDT"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['addreferral'])
def add_referral(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        update_user_activity(message.from_user.id)
        
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ استخدم: /addreferral [user_id]")
            return
        
        user_id = int(parts[1])
        
        user = get_user(user_id)
        user['referrals_count'] += 1
        user['referrals_new'] += 1
        user['balance'] += 1.0
        user['total_earned'] += 1.0
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم إضافة إحالة للمستخدم {user_id}\n🎁 مكافأة: 1 USDT\n👥 الإحالات الجديدة: {user['referrals_new']}\n👥 الإجمالي: {user['referrals_count']}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setvip'])
def set_vip(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        update_user_activity(message.from_user.id)
        
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /setvip [user_id] [level]\n\n0: مبتدئ\n1: برونز\n2: سيلفر\n3: جولد")
            return
        
        user_id = int(parts[1])
        vip_level = int(parts[2])
        
        if vip_level not in [0, 1, 2, 3]:
            bot.reply_to(message, "❌ مستوى VIP غير صحيح!\n\n0: مبتدئ\n1: برونز\n2: سيلفر\n3: جولد")
            return
        
        user = get_user(user_id)
        old_vip = get_vip_level_name(user['vip_level'])
        user['vip_level'] = vip_level
        new_vip = get_vip_level_name(user['vip_level'])
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم تعيين مستوى VIP للمستخدم {user_id}\n💎 السابق: {old_vip}\n💎 الجديد: {new_vip}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['userinfo'])
def user_info(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        update_user_activity(message.from_user.id)
        
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ استخدم: /userinfo [user_id]")
            return
        
        user_id = int(parts[1])
        user = get_user(user_id)
        
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
        last_active = user.get('last_activity', 'غير معروف')
        
        info_text = f"""
📊 معلومات المستخدم:

🆔 الآيدي: {user['user_id']}
👤 الاسم: {user['first_name']}
💰 الرصيد: {user['balance']:.1f} USDT
👥 الإحالات: {user['referrals_count']}
👥 الإحالات الجديدة: {user.get('referrals_new', 0)}/15
🎯 المحاولات: {user['games_played_today']}/{total_attempts} (متبقي: {remaining_attempts})
💎 VIP: {get_vip_level_name(user['vip_level'])}
🎮 الألعاب: {user['total_games_played']}
💳 الإيداعات: {user['total_deposits']:.1f} USDT
🏆 الأرباح: {user['total_earned']:.1f} USDT
📅 مسجل منذ: {user['registration_date']}
📅 أيام التسجيل: {user.get('registration_days', 0)} يوم
🕒 آخر نشاط: {last_active}"""
        
        bot.reply_to(message, info_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        update_user_activity(message.from_user.id)
        
        with db_lock:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE balance > 0 OR games_played_today > 0")
            active_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(balance) FROM users")
            total_balance = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(referrals_count) FROM users")
            total_referrals = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(total_deposits) FROM users")
            total_deposits = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE games_played_today > 0")
            today_players = cursor.fetchone()[0]
            
            cursor.execute("SELECT vip_level, COUNT(*) FROM users GROUP BY vip_level")
            vip_counts = {0: 0, 1: 0, 2: 0, 3: 0}
            for row in cursor.fetchall():
                vip_counts[row[0]] = row[1]
            
            conn.close()
        
        stats_text = f"""
📈 إحصائيات البوت:

👥 إجمالي المستخدمين: {total_users}
👤 المستخدمين النشطين: {active_users}
💰 إجمالي الرصيد: {total_balance:.1f} USDT
👥 إجمالي الإحالات: {total_referrals}
💳 إجمالي الإيداعات: {total_deposits:.1f} USDT
🎯 مستخدمين بلعبوا اليوم: {today_players}

💎 إحصائيات VIP:
🟢 مبتدئ: {vip_counts[0]}
🟢 برونز: {vip_counts[1]}  
🔵 سيلفر: {vip_counts[2]}
🟡 جولد: {vip_counts[3]}"""
        
        bot.reply_to(message, stats_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# ======================
# 🚀 تشغيل النظام مع إبقاء السيرفر شغال
# ======================

def keep_alive():
    """إبقاء السيرفر شغال دائماً"""
    while True:
        try:
            # الحصول على رابط التطبيق تلقائياً
            app_url = os.environ.get('RAILWAY_STATIC_URL', 'https://your-app-name.railway.app')
            requests.get(f'{app_url}/health', timeout=10)
            print("✅ تم إرسال طلب إبقاء السيرفر شغال")
            time.sleep(300)  # كل 5 دقائق
        except Exception as e:
            print(f"❌ فشل إبقاء السيرفر شغال: {e}")
            time.sleep(60)  # حاول مرة أخرى بعد دقيقة

def run_bot():
    """تشغيل البوت مع معالجة الأخطاء"""
    attempt = 0
    max_attempts = 10
    
    while attempt < max_attempts:
        try:
            print("=" * 50)
            print(f"🚀 STARTING USDT BOT - ATTEMPT {attempt + 1}/{max_attempts}")
            print("=" * 50)
            
            if not BOT_TOKEN:
                logger.error("❌ CRITICAL: BOT_TOKEN is not set!")
                return
            
            # تهيئة قاعدة البيانات
            if not init_database():
                logger.error("❌ فشل في تهيئة قاعدة البيانات!")
                time.sleep(10)
                attempt += 1
                continue
            
            print("✅ Database initialized successfully")
            print("🤖 Starting Telegram Bot Polling...")
            
            # إعدادات polling محسنة
            bot.polling(
                none_stop=True,
                timeout=90,
                long_polling_timeout=60,
                interval=1
            )
            
            # إذا وصلنا هنا، يعني ال polling توقف بشكل طبيعي
            print("🔄 Bot polling stopped normally, restarting...")
            break
            
        except Exception as e:
            attempt += 1
            logger.error(f"❌ BOT CRASHED (Attempt {attempt}/{max_attempts}): {repr(e)}")
            import traceback
            traceback.print_exc()
            
            if attempt < max_attempts:
                wait_time = min(attempt * 10, 60)  # زيادة وقت الانتظار تدريجياً
                print(f"🔄 Restarting in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("❌ MAXIMUM RESTART ATTEMPTS REACHED! Bot stopped.")
                break

def run_flask():
    """تشغيل Flask server"""
    while True:
        try:
            port = int(os.environ.get('PORT', 10000))
            print(f"🌐 Starting Flask server on port {port}...")
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        except Exception as e:
            logger.error(f"❌ Flask server crashed: {e}")
            print("🔄 Restarting Flask server in 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    print("🎯 Starting USDT Bot System with Auto-Restart...")
    
    # تشغيل keep-alive في thread منفصل
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    
    # تشغيل البوت في thread منفصل
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # تشغيل Flask في thread الرئيسي
    run_flask()
