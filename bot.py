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
import requests

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
YOUR_USER_ID = 8400225549  # آيديك الخاص

def is_admin(user_id):
    return user_id in ADMIN_IDS

# 🗄️ قاعدة البيانات
DB_FILE = 'usdt_bot.db'
db_lock = threading.Lock()

# مستويات VIP
VIP_LEVELS = {
    0: {"name": "🟢 مبتدئ", "daily_bonus": 0.8, "max_attempts": 3, "price": 0},
    1: {"name": "🟢 برونز", "daily_bonus": 1.25, "max_attempts": 5, "price": 5},
    2: {"name": "🔵 سيلفر", "daily_bonus": 1.75, "max_attempts": 8, "price": 10},
    3: {"name": "🟡 جولد", "daily_bonus": 2.75, "max_attempts": 13, "price": 20}
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
                last_mining_date TEXT,
                withdrawal_address TEXT,
                games_played_today INTEGER DEFAULT 0,
                last_reset_date TEXT,
                has_deposit INTEGER DEFAULT 0
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
                    'last_mining_date': user_data[12],
                    'withdrawal_address': user_data[13],
                    'games_played_today': user_data[14],
                    'last_reset_date': user_data[15],
                    'has_deposit': user_data[16]
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
                    'last_mining_date': None,
                    'withdrawal_address': "",
                    'games_played_today': 0,
                    'last_reset_date': datetime.now().strftime('%Y-%m-%d'),
                    'has_deposit': 0
                }
                cursor.execute("""
                    INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_user['user_id'], new_user['username'], new_user['first_name'],
                    new_user['balance'], new_user['referral_count'], new_user['new_referrals'],
                    new_user['vip_level'], new_user['attempts'], new_user['total_earnings'],
                    new_user['total_deposits'], new_user['registration_date'],
                    new_user['last_activity'], new_user['last_mining_date'],
                    new_user['withdrawal_address'], new_user['games_played_today'],
                    new_user['last_reset_date'], new_user['has_deposit']
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

def get_remaining_attempts(user):
    base_attempts = VIP_LEVELS[user['vip_level']]['max_attempts']
    extra_attempts = user.get('new_referrals', 0)
    used_attempts = user.get('games_played_today', 0)
    total_attempts = base_attempts + extra_attempts
    remaining = total_attempts - used_attempts
    return max(0, remaining), total_attempts, extra_attempts

def can_withdraw(user):
    """التحقق من إمكانية السحب"""
    has_10_days = True
    has_150_balance = user['balance'] >= 150
    has_address = bool(user.get('withdrawal_address', ''))
    has_15_refs = user.get('new_referrals', 0) >= 15
    has_deposit = user.get('has_deposit', 0) == 1
    
    return has_deposit and has_150_balance and has_address and has_15_refs

def get_mining_time_left(user_id):
    """حساب الوقت المتبقي للمكافأة اليومية - حقيقي"""
    user = get_user(user_id)
    if not user or not user['last_mining_date']:
        return "جاهز الآن! 🎁"
    
    try:
        last_mining = datetime.strptime(user['last_mining_date'], '%Y-%m-%d %H:%M:%S')
        next_mining = last_mining + timedelta(hours=24)
        now = datetime.now()
        
        if now >= next_mining:
            return "جاهز الآن! 🎁"
        
        time_left = next_mining - now
        hours = time_left.seconds // 3600
        minutes = (time_left.seconds % 3600) // 60
        seconds = time_left.seconds % 60
        
        # إرجاع وقت عشوائي بين 1-5 دقائق إذا كان أقل من 5 دقائق (للتجربة)
        if hours == 0 and minutes < 5:
            random_minutes = random.randint(1, 5)
            random_seconds = random.randint(1, 59)
            return f"{random_minutes:02d}:{random_seconds:02d} ⏳"
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d} ⏳"
    except:
        return "جاهز الآن! 🎁"

def claim_daily_bonus(user_id):
    """المطالبة بالمكافأة اليومية"""
    user = get_user(user_id)
    if not user:
        return False, "❌ المستخدم غير موجود"
    
    # التحقق إذا أخذ المكافأة اليوم
    if user.get('last_mining_date'):
        last_claim = datetime.strptime(user['last_mining_date'], '%Y-%m-%d %H:%M:%S')
        next_claim = last_claim + timedelta(hours=24)
        if datetime.now() < next_claim:
            time_left = next_claim - datetime.now()
            hours = time_left.seconds // 3600
            minutes = (time_left.seconds % 3600) // 60
            return False, f"⏳ انتظر {hours:02d}:{minutes:02d} للمكافأة التالية"
    
    # حساب المكافأة حسب مستوى VIP
    vip_info = VIP_LEVELS[user['vip_level']]
    daily_bonus = vip_info['daily_bonus']
    
    # إضافة المكافأة للرصيد
    new_balance = user['balance'] + daily_bonus
    new_earnings = user['total_earnings'] + daily_bonus
    
    success = update_user(
        user_id,
        balance=new_balance,
        total_earnings=new_earnings,
        last_mining_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    if success:
        return True, f"🎉 **تم استلام المكافأة اليومية!**\n💰 **المبلغ:** {daily_bonus:.2f} USDT\n💵 **الرصيد الجديد:** {new_balance:.2f} USDT"
    else:
        return False, "❌ فشل في استلام المكافأة"

def send_admin_notification(user, service_type, amount=0):
    """إرسال إشعار للمسؤول"""
    try:
        notification_text = f"""🆕 **طلب جديد من المستخدم**

👤 **المستخدم:** {user['first_name'] or 'غير معروف'}
🆔 **الآيدي:** {user['user_id']}
📞 **للتواصل:** [اضغط هنا](tg://user?id={user['user_id']})

📋 **نوع الخدمة:** {service_type}
{'💰 **المبلغ:** ' + str(amount) + ' USDT' if amount > 0 else ''}
💵 **رصيده الحالي:** {user['balance']:.1f} USDT
📅 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ **سيتم معالجة الطلب خلال 24 ساعة**"""
        
        bot.send_message(
            YOUR_USER_ID,
            notification_text,
            parse_mode='Markdown'
        )
        print(f"✅ تم إرسال إشعار للمسؤول عن {service_type}")
    except Exception as e:
        print(f"❌ خطأ في إرسال الإشعار: {e}")

# 🎯 الواجهة الرئيسية المحسنة
@bot.message_handler(commands=['start', 'profile', 'الملف'])
def handle_start(message):
    try:
        user_id = message.from_user.id
        print(f"📩 استلام /start من {user_id}")
        
        user_data = get_user(user_id)
        
        # تحديث بيانات المستخدم
        update_user(
            user_id,
            first_name=message.from_user.first_name or "",
            username=message.from_user.username or "",
            last_activity=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user_data)
        vip_info = VIP_LEVELS[user_data['vip_level']]
        
        # حساب الأيام منذ التسجيل
        reg_date = datetime.strptime(user_data['registration_date'].split()[0], '%Y-%m-%d')
        days_registered = (datetime.now() - reg_date).days
        
        # التحقق من إمكانية السحب
        can_withdraw_user = can_withdraw(user_data)
        
        profile_text = f"""
✨ **الملف الشخصي المتقدم** ✨

👤 **المستخدم:** {user_data['first_name'] or 'زائر جديد'}
🆔 **المعرف:** `{user_id}`
📅 **أيام العضوية:** {days_registered} يوم

💼 **الحالة المالية:**
├ 💰 **الرصيد:** `{user_data['balance']:.2f} USDT`
├ 💎 **إجمالي الأرباح:** `{user_data['total_earnings']:.2f} USDT`
└ 💳 **إجمالي الإيداعات:** `{user_data['total_deposits']:.2f} USDT`

🏆 **المستوى والصلاحيات:**
├ {vip_info['name']}
├ 🎯 **محاولات اليوم:** {remaining_attempts}/{total_attempts}
└ 👥 **الإحالات:** {user_data['referral_count']} مستخدم

⏰ **المكافأة اليومية:** {get_mining_time_left(user_id)}
🔐 **حالة السحب:** {'✅ **مفعل**' if can_withdraw_user else '❌ **غير مفعل**'}
📅 **تاريخ التسجيل:** {user_data['registration_date'].split()[0]}
        """
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        # الصف الأول
        keyboard.add(
            InlineKeyboardButton("🎮 ألعاب الربح", callback_data="games"),
            InlineKeyboardButton("💎 ترقية VIP", callback_data="vip_services")
        )
        
        # الصف الثاني
        keyboard.add(
            InlineKeyboardButton("👥 نظام الإحالات", callback_data="referral"),
            InlineKeyboardButton("💰 سحب الأرباح", callback_data="withdraw")
        )
        
        # الصف الثالث
        keyboard.add(
            InlineKeyboardButton("💳 إيداع الرصيد", callback_data="deposit"),
            InlineKeyboardButton("🎁 المكافأة اليومية", callback_data="daily_bonus")
        )
        
        # الصف الرابع
        keyboard.add(
            InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4"),
            InlineKeyboardButton("🔄 تحديث البيانات", callback_data="refresh_profile")
        )
        
        bot.send_message(
            user_id, 
            profile_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        print(f"✅ تم إرسال الواجهة المحسنة لـ {user_id}")
        
    except Exception as e:
        print(f"❌ خطأ في الواجهة المحسنة: {e}")

@bot.message_handler(commands=['myid'])
def handle_myid(message):
    try:
        bot.reply_to(message, f"🆔 معرفك: `{message.from_user.id}`", parse_mode='Markdown')
    except Exception as e:
        print(f"❌ خطأ في /myid: {e}")

# 🎮 معالجة الأزرار
@bot.callback_query_handler(func=lambda call: call.data == "start_main")
def handle_start_button(call):
    try:
        handle_start(call.message)
    except Exception as e:
        print(f"❌ خطأ في زر البدء: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "games")
def show_games(call):
    try:
        user = get_user(call.from_user.id)
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
        
        games_text = f"""🎮 **قائمة الألعاب**

🎯 **المحاولات المتبقية:** {remaining_attempts}/{total_attempts}
💰 **الربح لكل محاولة:** 2.5 USDT

اختر اللعبة:"""
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎰 سلوت", callback_data="game_slot"),
            InlineKeyboardButton("🎲 نرد", callback_data="game_dice")
        )
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        
        bot.edit_message_text(
            games_text, 
            call.message.chat.id, 
            call.message.message_id, 
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"❌ خطأ في show_games: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_profile")
def back_to_profile(call):
    try:
        handle_start(call.message)
    except Exception as e:
        print(f"❌ خطأ في back_to_profile: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "refresh_profile")
def refresh_profile(call):
    """تحديث البيانات وعرضها من جديد"""
    try:
        handle_start(call.message)
        bot.answer_callback_query(call.id, "✅ تم تحديث البيانات")
    except Exception as e:
        print(f"❌ خطأ في تحديث البيانات: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "daily_bonus")
def handle_daily_bonus(call):
    """المطالبة بالمكافأة اليومية"""
    try:
        success, message = claim_daily_bonus(call.from_user.id)
        bot.answer_callback_query(call.id, message, show_alert=True)
        
        if success:
            # تحديث الواجهة بعد أخذ المكافأة
            time.sleep(1)
            handle_start(call.message)
            
    except Exception as e:
        print(f"❌ خطأ في المكافأة اليومية: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ في استلام المكافأة", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "vip_services")
def show_vip_services(call):
    try:
        vip_text = """💎 **العضويات VIP المميزة:**

🟢 **برونز VIP - 5 USDT:**
• مكافأة يومية 1.25 USDT
• +2 محاولات ألعاب يومية
• دعم فني متميز

🔵 **سيلفر VIP - 10 USDT:**
• مكافأة يومية 1.75 USDT  
• +5 محاولات ألعاب يومية
• أولوية في معالجة طلبات السحب

🟡 **جولد VIP - 20 USDT:**
• مكافأة يومية 2.75 USDT
• +10 محاولات ألعاب يومية
• أولوية قصوى في جميع الخدمات

اختر العضوية المناسبة:"""
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("🟢 شراء برونز VIP - 5 USDT", callback_data="vip_bronze"),
            InlineKeyboardButton("🔵 شراء سيلفر VIP - 10 USDT", callback_data="vip_silver"),
            InlineKeyboardButton("🟡 شراء جولد VIP - 20 USDT", callback_data="vip_gold"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile")
        )
        
        bot.edit_message_text(
            vip_text, 
            call.message.chat.id, 
            call.message.message_id, 
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"❌ خطأ في show_vip_services: {e}")

# معالجة طلبات VIP
@bot.callback_query_handler(func=lambda call: call.data.startswith('vip_'))
def handle_vip_purchase(call):
    try:
        user = get_user(call.from_user.id)
        vip_type = call.data.replace('vip_', '')
        
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
        
        # إرسال إشعار للمسؤول
        send_admin_notification(user, f"شراء {vip_name}", vip_price)
        
        # إرسال رسالة تأكيد للمستخدم
        bot.send_message(
            call.from_user.id,
            f"✅ **تم إرسال طلب شراء {vip_name} بنجاح!**\n\n"
            f"💰 **السعر:** {vip_price} USDT\n"
            f"📞 **سيقوم المسؤول بالتواصل معك خلال 24 ساعة**\n\n"
            f"شكراً لثقتك بنا! 🌟",
            parse_mode='Markdown'
        )
        
        bot.answer_callback_query(call.id, f"✅ تم إرسال طلب {vip_name} للمسؤول")
        
    except Exception as e:
        print(f"❌ خطأ في handle_vip_purchase: {e}")

# 💳 زر الإيداع
@bot.callback_query_handler(func=lambda call: call.data == "deposit")
def handle_deposit(call):
    try:
        deposit_text = """💳 **نظام الإيداع**

📊 **لماذا تحتاج للإيداع؟**
• تفعيل خاصية السحب
• زيادة فرص الربح
• وصول أسرع للأرباح

💰 **الحد الأدنى للإيداع:** 10 USDT

🚀 **لإجراء الإيداع:**
1. اضغط على زر 'طلب إيداع' أدناه
2. سيتم تحويلك للمسؤول
3. أرسل مبلغ الإيداع
4. سيتم تفعيل حسابك خلال 24 ساعة

✅ **بعد الإيداع ستصبح مؤهلاً ل:**
• سحب الأرباح
• مزايا إضافية
• دعم متميز"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("📥 طلب إيداع", callback_data="request_deposit"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        
        bot.edit_message_text(
            deposit_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"❌ خطأ في handle_deposit: {e}")

# معالجة طلب الإيداع
@bot.callback_query_handler(func=lambda call: call.data == "request_deposit")
def handle_request_deposit(call):
    try:
        user = get_user(call.from_user.id)
        
        # إرسال إشعار للمسؤول
        send_admin_notification(user, "طلب إيداع", 10)
        
        # إرسال رسالة تأكيد للمستخدم
        bot.send_message(
            call.from_user.id,
            "✅ **تم إرسال طلب الإيداع بنجاح!**\n\n"
            "📞 **سيقوم المسؤول بالتواصل معك خلال 24 ساعة**\n"
            "💰 **الحد الأدنى للإيداع: 10 USDT**\n\n"
            "شكراً لثقتك بنا! 🌟",
            parse_mode='Markdown'
        )
        
        bot.answer_callback_query(call.id, "✅ تم إرسال طلب الإيداع للمسؤول")
        
    except Exception as e:
        print(f"❌ خطأ في handle_request_deposit: {e}")

# 🎯 رابط الاحالات
@bot.callback_query_handler(func=lambda call: call.data == "referral")
def handle_referral(call):
    try:
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start=ref{call.from_user.id}"
        
        referral_text = f"""🎯 **نظام الإحالات**

🔗 **رابط الدعوة الخاص بك:**
`{referral_link}`

👥 **مزايا الإحالات:**
• 🎁 1 USDT مكافأة فورية لكل إحالة
• +1 محاولة ألعاب يومية لكل إحالة  
• فرصة ربح مضاعفة
• وصول أسرع لشروط السحب

📤 **شارك الرابط مع أصدقائك واكسب المزيد!**"""
        
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
        
        if not user.get('has_deposit', 0):
            withdraw_text = """❌ **غير مؤهل للسحب**

💰 **لتصبح مؤهلاً للسحب، تحتاج إلى:**

1. **إيداع أولي:** 10 USDT كحد أدنى
2. **رصيد في الحساب:** 150 USDT كحد أدنى للسحب  
3. **إحالات جديدة:** 15 إحالة على الأقل
4. **عنوان محفظة:** USDT (TRC20)

💳 **لإجراء الإيداع، اضغط على زر 'الإيداع' في القائمة الرئيسية**"""
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("💳 الانتقال للإيداع", callback_data="deposit"))
            keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        elif not can_withdraw(user):
            withdraw_text = f"""❌ **غير مؤهل للسحب بعد**

💰 **الرصيد المتاح:** {user['balance']:.1f} USDT
💳 **عنوان المحفظة:** {user['withdrawal_address'] or 'غير محدد'}

📊 **الشروط المطلوبة:**
• ✓ إيداع مفعل
• {'✓' if user['balance'] >= 150 else '✗'} رصيد 150 USDT ({user['balance']:.1f}/150)
• {'✓' if user['new_referrals'] >= 15 else '✗'} 15 إحالة جديدة ({user['new_referrals']}/15)
• {'✓' if user['withdrawal_address'] else '✗'} عنوان محفظة محدد

🚫 **لا يمكنك السحب حتى تستكمل جميع الشروط**"""
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        else:
            withdraw_text = f"""💰 **نظام السحب**

✅ **أنت مؤهل للسحب!**

💰 **الرصيد المتاح:** {user['balance']:.1f} USDT
💳 **عنوان المحفظة:** {user['withdrawal_address']}

📊 **شروط السحب:**
• ✓ إيداع مفعل
• ✓ رصيد 150 USDT
• ✓ 15 إحالة جديدة
• ✓ عنوان محفظة محدد

اختر مبلغ السحب:"""
            
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton("💰 سحب 150 USDT", callback_data="withdraw_150"),
                InlineKeyboardButton("💰 سحب 300 USDT", callback_data="withdraw_300"),
                InlineKeyboardButton("💰 سحب 500 USDT", callback_data="withdraw_500"),
                InlineKeyboardButton("💰 سحب كل الرصيد", callback_data="withdraw_all")
            )
            keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        
        bot.edit_message_text(
            withdraw_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"❌ خطأ في handle_withdraw: {e}")

# معالجة طلبات السحب
@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_'))
def handle_withdraw_request(call):
    try:
        user = get_user(call.from_user.id)
        
        if not can_withdraw(user):
            bot.answer_callback_query(call.id, "❌ لست مؤهلاً للسحب بعد!", show_alert=True)
            return
        
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
        
        # إرسال إشعار للمسؤول
        send_admin_notification(user, f"طلب سحب", amount)
        
        # إرسال رسالة تأكيد للمستخدم
        bot.send_message(
            call.from_user.id,
            f"✅ **تم إرسال طلب السحب بنجاح!**\n\n"
            f"💰 **المبلغ:** {amount:.1f} USDT\n"
            f"💳 **العنوان:** {user['withdrawal_address']}\n"
            f"📞 **سيتم معالجة طلبك خلال 24 ساعة**\n\n"
            f"شكراً لاستخدامك خدماتنا! 🌟",
            parse_mode='Markdown'
        )
        
        bot.answer_callback_query(call.id, f"✅ تم إرسال طلب سحب {amount:.1f} USDT للمسؤول")
        
    except Exception as e:
        print(f"❌ خطأ في handle_withdraw_request: {e}")

# 🎰 لعبة السلوت
@bot.callback_query_handler(func=lambda call: call.data == "game_slot")
def play_slot(call):
    try:
        user = get_user(call.from_user.id)
        remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
        
        if remaining_attempts <= 0:
            bot.answer_callback_query(call.id, "❌ لا توجد محاولات متبقية اليوم!", show_alert=True)
            return
        
        update_user(call.from_user.id, games_played_today=user.get('games_played_today', 0) + 1)
        
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
        
        new_balance = user['balance'] + win_amount
        new_earnings = user['total_earnings'] + win_amount
        update_user(call.from_user.id, balance=new_balance, total_earnings=new_earnings)
        
        user = get_user(call.from_user.id)
        remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
        
        game_result = f"""🎰 **لعبة السلوت**

{' | '.join(result)}

{win_text}
💰 **الربح:** {win_amount:.2f} USDT
💵 **الرصيد الجديد:** {new_balance:.2f} USDT

🎯 **المحاولات المتبقية:** {remaining_attempts}/{total_attempts}"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🎰 العب مرة أخرى", callback_data="game_slot"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع للألعاب", callback_data="games"))
        
        bot.edit_message_text(
            game_result, 
            call.message.chat.id, 
            call.message.message_id, 
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
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
        
        update_user(call.from_user.id, games_played_today=user.get('games_played_today', 0) + 1)
        
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
        
        new_balance = user['balance'] + win_amount
        new_earnings = user['total_earnings'] + win_amount
        update_user(call.from_user.id, balance=new_balance, total_earnings=new_earnings)
        
        user = get_user(call.from_user.id)
        remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
        
        game_result = f"""🎲 **لعبة النرد**

🎲 **النرد:** {dice1} + {dice2} = {total}

{win_text}
💰 **الربح:** {win_amount:.2f} USDT
💵 **الرصيد الجديد:** {new_balance:.2f} USDT

🎯 **المحاولات المتبقية:** {remaining_attempts}/{total_attempts}"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🎲 العب مرة أخرى", callback_data="game_dice"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع للألعاب", callback_data="games"))
        
        bot.edit_message_text(
            game_result, 
            call.message.chat.id, 
            call.message.message_id, 
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"❌ خطأ في play_dice: {e}")

# 🛠️ الأوامر الإدارية (نفسها موجودة بالكود السابق - محفوظة كما هي)
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
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
        
        info_msg = f"👤 **معلومات المستخدم:**\n\n"
        info_msg += f"🆔 **المعرف:** {user['user_id']}\n"
        info_msg += f"👤 **الاسم:** {user['first_name'] or 'غير معروف'}\n"
        info_msg += f"📛 **اليوزر:** @{user['username'] or 'لا يوجد'}\n"
        info_msg += f"💰 **الرصيد:** {user['balance']:.2f} USDT\n"
        info_msg += f"👥 **الإحالات:** {user['referral_count']}\n"
        info_msg += f"📈 **الإحالات الجديدة:** {user['new_referrals']}/15\n"
        info_msg += f"🏆 **مستوى VIP:** {vip_info['name']} (المستوى {user['vip_level']})\n"
        info_msg += f"🎯 **المحاولات:** {user['attempts']} (متبقي: {remaining_attempts}/{total_attempts})\n"
        info_msg += f"🎮 **ألعاب اليوم:** {user.get('games_played_today', 0)}\n"
        info_msg += f"💎 **إجمالي الأرباح:** {user['total_earnings']:.2f} USDT\n"
        info_msg += f"💳 **إجمالي الإيداعات:** {user['total_deposits']:.2f} USDT\n"
        info_msg += f"✅ **إيداع مفعل:** {'نعم' if user.get('has_deposit', 0) else 'لا'}\n"
        info_msg += f"📅 **تاريخ التسجيل:** {user['registration_date']}\n"
        info_msg += f"🕒 **آخر نشاط:** {user['last_activity']}\n"
        if user.get('withdrawal_address'):
            info_msg += f"💳 **عنوان السحب:** {user['withdrawal_address']}\n"
        
        bot.send_message(message.chat.id, info_msg, parse_mode='Markdown')
        
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
        
        cursor.execute("SELECT user_id, first_name, balance, vip_level, registration_date FROM users ORDER BY registration_date DESC LIMIT 20")
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            bot.send_message(message.chat.id, "❌ لا يوجد مستخدمين!")
            return
        
        users_msg = f"👥 **قائمة المستخدمين** (آخر 20 من أصل {total_users}):\n\n"
        
        for i, user in enumerate(users, 1):
            vip_name = VIP_LEVELS[user[3]]['name']
            users_msg += f"{i}. {user[1] or 'غير معروف'} (ID: {user[0]})\n"
            users_msg += f"   💰 {user[2]:.2f} USDT | {vip_name} | {user[4][:10]}\n\n"
        
        bot.send_message(message.chat.id, users_msg, parse_mode='Markdown')
        
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
        
        cursor.execute("SELECT SUM(total_deposits) as total_deposits FROM users")
        total_deposits = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(referral_count) as total_referrals FROM users")
        total_referrals = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT vip_level, COUNT(*) as count FROM users GROUP BY vip_level")
        vip_stats = cursor.fetchall()
        
        conn.close()
        
        stats_msg = "📊 **إحصائيات البوت:**\n\n"
        stats_msg += f"👥 **إجمالي المستخدمين:** {total_users}\n"
        stats_msg += f"💰 **إجمالي الرصيد:** {total_balance:.2f} USDT\n"
        stats_msg += f"💎 **إجمالي الأرباح:** {total_earnings:.2f} USDT\n"
        stats_msg += f"💳 **إجمالي الإيداعات:** {total_deposits:.2f} USDT\n"
        stats_msg += f"👥 **إجمالي الإحالات:** {total_referrals}\n\n"
        
        stats_msg += "🏆 **توزيع مستويات VIP:**\n"
        for level, count in vip_stats:
            vip_name = VIP_LEVELS[level]['name']
            stats_msg += f"{vip_name}: {count} مستخدم\n"
        
        bot.send_message(message.chat.id, stats_msg, parse_mode='Markdown')
        
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
            bot.send_message(message.chat.id, "❌ مستوى VIP غير صحيح!\n\n0: مبتدئ\n1: برونز\n2: سيلفر\n3: جولد")
            return
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        old_vip = VIP_LEVELS[user['vip_level']]['name']
        success = update_user(target_user_id, vip_level=vip_level)
        new_vip = VIP_LEVELS[vip_level]['name']
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين مستوى VIP للمستخدم {target_user_id}\n💎 السابق: {old_vip}\n💎 الجديد: {new_vip}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين مستوى VIP!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['activate_deposit'])
def handle_activate_deposit(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "📝 usage: /activate_deposit [user_id]")
            return
        
        target_user_id = parts[1]
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        success = update_user(target_user_id, has_deposit=1)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تفعيل الإيداع للمستخدم {target_user_id}")
            # إرسال إشعار للمستخدم
            try:
                bot.send_message(
                    target_user_id,
                    "🎉 **تم تفعيل إيداعك بنجاح!**\n\n"
                    "✅ **أنت الآن مؤهل ل:**\n"
                    "• سحب الأرباح\n"
                    "• مزايا إضافية\n"
                    "• دعم متميز\n\n"
                    "شكراً لثقتك بنا! 🌟",
                    parse_mode='Markdown'
                )
            except:
                pass
        else:
            bot.send_message(message.chat.id, "❌ فشل في تفعيل الإيداع!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['withdraw_balance'])
def handle_withdraw_balance(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /withdraw_balance [user_id] [amount]")
            return
        
        target_user_id = parts[1]
        amount = float(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        if user['balance'] < amount:
            bot.send_message(message.chat.id, f"❌ رصيد المستخدم غير كافي! الرصيد: {user['balance']:.1f} USDT")
            return
        
        new_balance = user['balance'] - amount
        success = update_user(target_user_id, balance=new_balance)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم سحب {amount} USDT من المستخدم {target_user_id}")
            # إرسال إشعار للمستخدم
            try:
                bot.send_message(
                    target_user_id,
                    f"💸 **تم سحب رصيد بنجاح!**\n\n"
                    f"💰 **المبلغ المسحوب:** {amount:.1f} USDT\n"
                    f"💵 **الرصيد المتبقي:** {new_balance:.1f} USDT\n"
                    f"📅 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"شكراً لاستخدامك خدماتنا! 🌟",
                    parse_mode='Markdown'
                )
            except:
                pass
        else:
            bot.send_message(message.chat.id, "❌ فشل في سحب الرصيد!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

# 🔧 نظام التشغيل المحسن مع ميزة عدم النوم
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 البوت شغال! أرسل /start للبدء"

@app.route('/health')
def health():
    return "✅ OK", 200

@app.route('/keepalive')
def keepalive():
    """لإبقاء البوت مستيقظاً"""
    return "🔄 البوت نشط", 200

def run_bot():
    """تشغيل البوت مع استقرار محسن"""
    print("🔄 بدء تشغيل البوت...")
    
    # تنظيف كامل
    try:
        bot.remove_webhook()
        time.sleep(3)
        print("✅ تم تنظيف الـ webhook")
    except Exception as e:
        print(f"⚠️  تنظيف webhook: {e}")
    
    # تهيئة قاعدة البيانات
    if not init_database():
        print("⚠️  تم المتابعة بدون قاعدة البيانات")
    
    # التشغيل الرئيسي مع معالجة أفضل للأخطاء
    while True:
        try:
            print("🚀 البوت يعمل الآن...")
            bot.infinity_polling(
                timeout=90,
                long_polling_timeout=45,
                skip_pending=True,
                allowed_updates=['message', 'callback_query']
            )
        except Exception as e:
            print(f"❌ خطأ في البوت: {e}")
            print("🔄 إعادة التشغيل بعد 20 ثانية...")
            time.sleep(20)

def run_flask_server():
    """تشغيل Flask في thread منفصل"""
    print("🌐 تشغيل خادم Flask...")
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

def keep_alive():
    """إرسال طلبات دورية لإبقاء البوت مستيقظاً"""
    import requests
    while True:
        try:
            # احصل على رابط التطبيق تلقائياً من متغير البيئة
            app_url = os.environ.get('RENDER_EXTERNAL_URL', '')
            if app_url:
                requests.get(f'{app_url}/health', timeout=10)
                requests.get(f'{app_url}/keepalive', timeout=10)
                print("🔄 تم إرسال طلب إبقاء البوت نشط")
            else:
                print("⚠️  لم يتم العثور على رابط التطبيق")
        except Exception as e:
            print(f"⚠️  فشل في إرسال طلب الإبقاء: {e}")
        time.sleep(300)  # كل 5 دقائق

if __name__ == "__main__":
    print("🎯 نظام البوت - الإصدار المستقر")
    
    # تشغيل Flask في thread منفصل
    import threading
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    # تشغيل نظام الإبقاء نشطاً
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    
    # انتظار قليل ثم تشغيل البوت
    time.sleep(8)
    
    # تشغيل البوت
    run_bot()
