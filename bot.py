import os
import telebot
import sqlite3
import random
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import time
from flask import Flask
import logging

# ✅ تفعيل السجلات
logging.basicConfig(level=logging.INFO)
print("🚀 بدء تشغيل البوت...")

# فحص BOT_TOKEN
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN غير موجود!")
    exit(1)

# تعريف البوت
bot = telebot.TeleBot(BOT_TOKEN)

# 🔐 إعدادات المشرفين
ADMIN_IDS = [8400225549]

def is_admin(user_id):
    return user_id in ADMIN_IDS

# 🗄️ قاعدة البيانات
DB_FILE = 'usdt_bot.db'
db_lock = threading.Lock()

# مستويات VIP
VIP_LEVELS = {
    0: {"name": "🟢 مبتدئ", "max_attempts": 3},
    1: {"name": "🟢 برونز", "max_attempts": 5},
    2: {"name": "🔵 سيلفر", "max_attempts": 8},
    3: {"name": "🟡 جولد", "max_attempts": 13}
}

def init_database():
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
                withdrawal_address TEXT,
                games_played_today INTEGER DEFAULT 0,
                last_reset_date TEXT
            )
        """)
        conn.commit()
        conn.close()
        print("✅ تم تهيئة قاعدة البيانات")
        return True
    except Exception as e:
        print(f"❌ خطأ في قاعدة البيانات: {e}")
        return False

def get_user(user_id):
    user_id_str = str(user_id)
    with db_lock:
        try:
            conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id_str,))
            user_data = cursor.fetchone()
            
            if user_data:
                user_dict = {
                    'user_id': user_data[0],
                    'username': user_data[1],
                    'first_name': user_data[2],
                    'balance': user_data[3],
                    'referral_count': user_data[4],
                    'new_referrals': user_data[5],
                    'vip_level': user_data[6],
                    'attempts': user_data[7],
                    'total_earnings': user_data[8],
                    'total_deposits': user_data[9],
                    'registration_date': user_data[10],
                    'last_activity': user_data[11],
                    'withdrawal_address': user_data[12],
                    'games_played_today': user_data[13],
                    'last_reset_date': user_data[14]
                }
                conn.close()
                return user_dict
            else:
                # إنشاء مستخدم جديد
                new_user = {
                    'user_id': user_id_str,
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
                    'withdrawal_address': "",
                    'games_played_today': 0,
                    'last_reset_date': datetime.now().strftime('%Y-%m-%d')
                }
                cursor.execute("""
                    INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_user['user_id'], new_user['username'], new_user['first_name'],
                    new_user['balance'], new_user['referral_count'], new_user['new_referrals'],
                    new_user['vip_level'], new_user['attempts'], new_user['total_earnings'],
                    new_user['total_deposits'], new_user['registration_date'],
                    new_user['last_activity'], new_user['withdrawal_address'],
                    new_user['games_played_today'], new_user['last_reset_date']
                ))
                conn.commit()
                conn.close()
                return new_user
                
        except Exception as e:
            print(f"❌ خطأ في جلب المستخدم: {e}")
            return None

def update_user(user_id, **kwargs):
    try:
        user = get_user(user_id)
        if not user:
            return False
            
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        # بناء query التحديث
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(user_id)
        
        cursor.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ خطأ في تحديث المستخدم: {e}")
        return False

# 🎯 الدالة الرئيسية للـ Start
@bot.message_handler(commands=['start', 'بدء', 'البدء'])
def handle_start(message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name or "مستخدم"
        username = message.from_user.username or ""
        
        print(f"🎯 استلام /start من {user_id} - {first_name}")
        
        # الحصول على بيانات المستخدم أو إنشاؤه
        user_data = get_user(user_id)
        
        if user_data:
            # تحديث بيانات المستخدم
            update_user(
                user_id,
                first_name=first_name,
                username=username,
                last_activity=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
        
        # إنشاء واجهة المستخدم الرئيسية
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
        
        # رسالة الترحيب
        welcome_text = f"""🎯 **مرحباً بك!**

👤 {first_name}
🆔 {user_id}
💰 الرصيد: {user_data['balance']:.2f} USDT

اختر من القائمة:"""
        
        bot.send_message(
            user_id,
            welcome_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        print(f"✅ تم إرسال الترحيب لـ {user_id}")
        
    except Exception as e:
        print(f"❌ خطأ في /start: {e}")

# 🆔 دالة الـ myid
@bot.message_handler(commands=['myid'])
def handle_myid(message):
    try:
        user_id = message.from_user.id
        bot.reply_to(message, f"🆔 معرفك: `{user_id}`", parse_mode='Markdown')
    except Exception as e:
        print(f"❌ خطأ في /myid: {e}")

# 🎮 معالجة الأزرار
@bot.callback_query_handler(func=lambda call: call.data == "games")
def show_games(call):
    try:
        user = get_user(call.from_user.id)
        vip_info = VIP_LEVELS[user['vip_level']]
        
        games_text = f"""🎮 قائمة الألعاب

المحاولات المتاحة: {user['attempts']}
🎰 الربح لكل محاولة: 2.5 USDT

اختر اللعبة:"""
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎰 سلوت", callback_data="game_slot"),
            InlineKeyboardButton("🎲 نرد", callback_data="game_dice")
        )
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        
        bot.edit_message_text(
            games_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ خطأ في show_games: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main(call):
    try:
        handle_start(call.message)
    except Exception as e:
        print(f"❌ خطأ في back_to_main: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "vip_services")
def show_vip_services(call):
    try:
        vip_text = """💎 خدمات VIP:

🟢 برونز - 5 USDT
🔵 سيلفر - 10 USDT  
🟡 جولد - 20 USDT

اختر العضوية:"""
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("🟢 شراء برونز", callback_data="buy_bronze"),
            InlineKeyboardButton("🔵 شراء سيلفر", callback_data="buy_silver"),
            InlineKeyboardButton("🟡 شراء جولد", callback_data="buy_gold"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
        )
        
        bot.edit_message_text(
            vip_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ خطأ في show_vip_services: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "referral")
def handle_referral(call):
    try:
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start=ref{call.from_user.id}"
        
        referral_text = f"""🎯 نظام الإحالات

🔗 رابطك: `{referral_link}`

مكافأة 1 USDT لكل إحالة!"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("📤 مشاركة", url=f"https://t.me/share/url?url={referral_link}"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        
        bot.edit_message_text(
            referral_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ خطأ في handle_referral: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def handle_withdraw(call):
    try:
        user = get_user(call.from_user.id)
        
        withdraw_text = f"""💰 السحب

💰 الرصيد: {user['balance']:.1f} USDT
💳 العنوان: {user['withdrawal_address'] or 'غير محدد'}

الحد الأدنى: 150 USDT"""
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("💰 150 USDT", callback_data="withdraw_150"),
            InlineKeyboardButton("💰 300 USDT", callback_data="withdraw_300"),
            InlineKeyboardButton("💰 500 USDT", callback_data="withdraw_500")
        )
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        
        bot.edit_message_text(
            withdraw_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ خطأ في handle_withdraw: {e}")

# 🎰 الألعاب
@bot.callback_query_handler(func=lambda call: call.data == "game_slot")
def play_slot(call):
    try:
        user = get_user(call.from_user.id)
        
        if user['attempts'] <= 0:
            bot.answer_callback_query(call.id, "❌ لا توجد محاولات!", show_alert=True)
            return
        
        # خصم محاولة
        update_user(call.from_user.id, attempts=user['attempts']-1)
        
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
        
        # إضافة الربح
        new_balance = user['balance'] + win_amount
        new_earnings = user['total_earnings'] + win_amount
        update_user(
            call.from_user.id, 
            balance=new_balance,
            total_earnings=new_earnings
        )
        
        game_result = f"""🎰 السلوت

{' | '.join(result)}

{win_text}
💰 الربح: {win_amount:.2f} USDT
💵 الرصيد: {new_balance:.2f} USDT"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🎰 العب مرة أخرى", callback_data="game_slot"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="games"))
        
        bot.edit_message_text(
            game_result,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ خطأ في play_slot: {e}")

# 🛠️ الأوامر الإدارية
@bot.message_handler(commands=['quickadd'])
def handle_quickadd(message):
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

@bot.message_handler(commands=['setbalance'])
def handle_setbalance(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
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
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
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
        
        success = update_user(target_user_id, referral_count=count, new_referrals=count)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين إحالات المستخدم {target_user_id} إلى {count}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين الإحالات!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['addreferral'])
def handle_addreferral(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
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
        new_refs = user['new_referrals'] + 1
        success = update_user(target_user_id, referral_count=new_count, new_referrals=new_refs)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم إضافة إحالة للمستخدم {target_user_id}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إضافة الإحالة!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setattempts'])
def handle_setattempts(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
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
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
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
        
        base_attempts = VIP_LEVELS[user['vip_level']]['max_attempts']
        success = update_user(target_user_id, attempts=base_attempts, games_played_today=0)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم إعادة تعيين محاولات المستخدم {target_user_id} إلى {base_attempts}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إعادة تعيين المحاولات!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['addattempts'])
def handle_addattempts(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
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
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
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
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
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
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
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
        info_msg += f"📈 الإحالات الجديدة: {user['new_referrals']}\n"
        info_msg += f"🏆 مستوى VIP: {vip_info['name']}\n"
        info_msg += f"🎯 المحاولات: {user['attempts']}\n"
        info_msg += f"💎 إجمالي الأرباح: {user['total_earnings']:.2f} USDT\n"
        info_msg += f"💳 إجمالي الإيداعات: {user['total_deposits']:.2f} USDT\n"
        
        bot.send_message(message.chat.id, info_msg)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['listusers'])
def handle_listusers(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
        return
    
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT user_id, first_name, balance, vip_level FROM users LIMIT 20")
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            bot.send_message(message.chat.id, "❌ لا يوجد مستخدمين!")
            return
        
        users_msg = f"👥 المستخدمين (آخر 20 من أصل {total_users}):\n\n"
        
        for i, user in enumerate(users, 1):
            vip_name = VIP_LEVELS[user[3]]['name']
            users_msg += f"{i}. {user[1] or 'غير معروف'} (ID: {user[0]})\n"
            users_msg += f"   💰 {user[2]:.2f} USDT | {vip_name}\n\n"
        
        bot.send_message(message.chat.id, users_msg)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['stats'])
def handle_stats(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
        return
    
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total_users FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(balance) as total_balance FROM users")
        total_balance = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(total_earnings) as total_earnings FROM users")
        total_earnings = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(referral_count) as total_referrals FROM users")
        total_referrals = cursor.fetchone()[0] or 0
        
        conn.close()
        
        stats_msg = "📊 إحصائيات البوت:\n\n"
        stats_msg += f"👥 إجمالي المستخدمين: {total_users}\n"
        stats_msg += f"💰 إجمالي الرصيد: {total_balance:.2f} USDT\n"
        stats_msg += f"💎 إجمالي الأرباح: {total_earnings:.2f} USDT\n"
        stats_msg += f"👥 إجمالي الإحالات: {total_referrals}\n"
        
        bot.send_message(message.chat.id, stats_msg)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setvip'])
def handle_setvip(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /setvip [user_id] [level]\n\n0: مبتدئ\n1: برونز\n2: سيلفر\n3: جولد")
            return
        
        target_user_id = parts[1]
        vip_level = int(parts[2])
        
        if vip_level not in [0, 1, 2, 3]:
            bot.send_message(message.chat.id, "❌ مستوى VIP غير صحيح!")
            return
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        success = update_user(target_user_id, vip_level=vip_level)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين مستوى VIP للمستخدم {target_user_id} إلى {VIP_LEVELS[vip_level]['name']}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين مستوى VIP!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

# 🔧 نظام التشغيل
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 البوت شغال! أرسل /start للبدء"

@app.route('/health')
def health():
    return "✅ OK", 200

def run_bot():
    """تشغيل البوت"""
    print("🔄 بدء تشغيل البوت...")
    
    # تنظيف webhook
    try:
        bot.delete_webhook()
        time.sleep(5)
    except:
        pass
    
    # تهيئة قاعدة البيانات
    init_database()
    
    # التشغيل الرئيسي
    while True:
        try:
            print("🚀 البوت يعمل الآن...")
            bot.infinity_polling(timeout=60, skip_pending=True)
        except Exception as e:
            print(f"❌ خطأ: {e}")
            print("🔄 إعادة التشغيل بعد 10 ثوان...")
            time.sleep(10)

if __name__ == "__main__":
    print("🎯 نظام البوت - الإصدار النهائي")
    
    # تشغيل Flask في الخلفية
    def run_flask():
        app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
    
    import threading
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # تشغيل البوت
    run_bot()
