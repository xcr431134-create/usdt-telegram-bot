import os
import telebot
import json
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

BOT_TOKEN = "7973697789:AAFXfYXTgYaTAF1j7IGhp2kiv-kxrN1uImk"
bot = telebot.TeleBot(BOT_TOKEN)
ADMIN_IDS = [8400225549]

# ملف تخزين البيانات
DATA_FILE = "users_data.json"

def load_users():
    """تحميل البيانات من الملف"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"❌ خطأ في تحميل البيانات: {e}")
        return {}

def save_users(users_data):
    """حفظ البيانات في الملف"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ خطأ في حفظ البيانات: {e}")
        return False

def get_user(user_id):
    """جلب بيانات المستخدم"""
    users_data = load_users()
    user_id_str = str(user_id)
    
    if user_id_str in users_data:
        # تحديث المحاولات إذا انتهى اليوم
        user_data = users_data[user_id_str]
        last_reset = user_data.get('last_reset_date', '2000-01-01')
        today = datetime.now().strftime('%Y-%m-%d')
        
        if last_reset != today:
            user_data['games_played_today'] = 0
            user_data['last_reset_date'] = today
            save_users(users_data)
        
        return user_data
    
    # إنشاء مستخدم جديد
    user_data = {
        'user_id': user_id_str,
        'username': "",
        'first_name': "",
        'balance': 0.0,
        'referrals_count': 0,
        'referrals_new': 0,
        'games_played_today': 0,
        'total_games_played': 0,
        'total_earned': 0.0,
        'total_deposits': 0.0,
        'vip_level': 0,
        'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_activity': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_reset_date': datetime.now().strftime('%Y-%m-%d')
    }
    
    users_data[user_id_str] = user_data
    save_users(users_data)
    return user_data

def save_user(user_data):
    """حفظ بيانات مستخدم"""
    users_data = load_users()
    users_data[user_data['user_id']] = user_data
    return save_users(users_data)

def update_user_activity(user_id):
    user = get_user(user_id)
    user['last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
    """وقت مكافأة التعدين (عشوائي)"""
    hours = random.randint(12, 20)
    minutes = random.randint(0, 59)
    return f"{hours}س {minutes}د ⏳"

# 🎯 الواجهة الرئيسية الجديدة
@bot.message_handler(commands=['start', 'profile'])
def start_command(message):
    user = get_user(message.from_user.id)
    user['first_name'] = message.from_user.first_name or ""
    user['username'] = message.from_user.username or ""
    update_user_activity(message.from_user.id)
    
    # حساب المحاولات المتبقية
    remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
    vip_name = get_vip_level_name(user['vip_level'])
    mining_time = get_mining_reward_time()
    
    # النص الرئيسي
    profile_text = f"""📊 الملف الشخصي

👤 المستخدم: {user['first_name'] or 'User'} 
🆔 المعرف: {user['user_id']}
💰 الرصيد: {user['balance']:.1f} USDT
👥 الإحالات: {user['referrals_count']} مستخدم
📈 الإحالات الجديدة: {user.get('referrals_new', 0)}/{user['referrals_count']}
🏆 مستوى VIP: {vip_name}
🎯 المحاولات المتبقية: {remaining_attempts} ({total_attempts} أساسية + {extra_attempts} إضافية)

⏰ مكافأة التعدين: {mining_time}

💎 إجمالي الأرباح: {user['total_earned']:.1f} USDT
💳 إجمالي الإيداعات: {user['total_deposits']:.1f} USDT
📅 تاريخ التسجيل: {user['registration_date'].split()[0]}"""

    # الأزرار
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎮 الألعاب", callback_data="games"),
        InlineKeyboardButton("💎 خدمات VIP", callback_data="vip_services"),
        InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral"),
        InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4"),
        InlineKeyboardButton("🔄 تحديث", callback_data="refresh_profile")
    )
    
    bot.send_message(message.chat.id, profile_text, reply_markup=keyboard)

# 🎮 قائمة الألعاب
@bot.callback_query_handler(func=lambda call: call.data == "games")
def show_games(call):
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

# 🎰 لعبة السلوت
@bot.callback_query_handler(func=lambda call: call.data == "game_slot")
def play_slot(call):
    user = get_user(call.from_user.id)
    remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
    
    if remaining_attempts <= 0:
        bot.answer_callback_query(call.id, "❌ لا توجد محاولات متبقية اليوم!", show_alert=True)
        return
    
    # خفض المحاولات
    user['games_played_today'] += 1
    user['total_games_played'] += 1
    
    # محاكاة لعبة السلوت
    symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎"]
    result = [random.choice(symbols) for _ in range(3)]
    
    # حساب الربح
    if result[0] == result[1] == result[2]:
        win_amount = 2.5
        win_text = "🎉 ربح كبير!"
    elif result[0] == result[1] or result[1] == result[2]:
        win_amount = 1.25
        win_text = "👍 ربح جيد!"
    else:
        win_amount = 0
        win_text = "😞 حاول مرة أخرى"
    
    # تحديث الرصيد
    user['balance'] += win_amount
    if win_amount > 0:
        user['total_earned'] += win_amount
    
    save_user(user)
    
    # تحديث المحاولات المتبقية
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

# 🎲 لعبة النرد
@bot.callback_query_handler(func=lambda call: call.data == "game_dice")
def play_dice(call):
    user = get_user(call.from_user.id)
    remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
    
    if remaining_attempts <= 0:
        bot.answer_callback_query(call.id, "❌ لا توجد محاولات متبقية اليوم!", show_alert=True)
        return
    
    # خفض المحاولات
    user['games_played_today'] += 1
    user['total_games_played'] += 1
    
    # محاكاة لعبة النرد
    dice1 = random.randint(1, 6)
    dice2 = random.randint(1, 6)
    total = dice1 + dice2
    
    # حساب الربح
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
    
    # تحديث الرصيد
    user['balance'] += win_amount
    if win_amount > 0:
        user['total_earned'] += win_amount
    
    save_user(user)
    
    # تحديث المحاولات المتبقية
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

# 💎 خدمات VIP
@bot.callback_query_handler(func=lambda call: call.data == "vip_services")
def show_vip_services(call):
    vip_text = """💎 العضويات VIP المميزة:

• 🟢 برونز VIP: +10% تعدين، مكافأة يومية 0.5 USDT
• 🔵 سيلفر VIP: +25% تعدين، مكافأة يومية 1.0 USDT  
• 🟡 جولد VIP: +50% تعدين، مكافأة يومية 2.0 USDT

اختر العضوية المناسبة:"""
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🟢 شراء برونز VIP", callback_data="buy_bronze"),
        InlineKeyboardButton("🔵 شراء سيلفر VIP", callback_data="buy_silver"),
        InlineKeyboardButton("🟡 شراء جولد VIP", callback_data="buy_gold"),
        InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile")
    )
    
    bot.edit_message_text(vip_text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

# إرسال طلبات الشراء للادمن
@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_vip_purchase(call):
    user = get_user(call.from_user.id)
    vip_type = call.data.replace('buy_', '')
    
    vip_names = {
        'bronze': '🟢 برونز VIP',
        'silver': '🔵 سيلفر VIP', 
        'gold': '🟡 جولد VIP'
    }
    
    vip_name = vip_names.get(vip_type, 'VIP')
    
    # إرسال طلب الشراء للادمن
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(
                admin_id,
                f"🛒 طلب شراء جديد:\n\n"
                f"👤 المستخدم: {user['first_name']} ({user['user_id']})\n"
                f"💎 النوع: {vip_name}\n"
                f"📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"⏰ الرجاء التواصل مع المستخدم لتأكيد الطلب"
            )
        except:
            pass
    
    # تأكيد للمستخدم
    bot.answer_callback_query(
        call.id, 
        f"✅ تم إرسال طلب شراء {vip_name} للإدارة\nسيتم التواصل معك قريباً", 
        show_alert=True
    )

# 🔄 تحديث الملف الشخصي
@bot.callback_query_handler(func=lambda call: call.data == "refresh_profile")
def refresh_profile(call):
    start_command(call.message)
    bot.answer_callback_query(call.id, "✅ تم التحديث")

# 🔙 رجوع للبروفايل
@bot.callback_query_handler(func=lambda call: call.data == "back_to_profile")
def back_to_profile(call):
    start_command(call.message)

# 🎯 رابط الاحالات
@bot.callback_query_handler(func=lambda call: call.data == "referral")
def handle_referral(call):
    update_user_activity(call.from_user.id)
    referral_link = f"https://t.me/{bot.get_me().username}?start=ref{call.from_user.id}"
    bot.edit_message_text(
        f"🎯 رابطك الخاص:\n`{referral_link}`\n\n"
        f"👥 كل ما يدخل شخص من الرابط تحصل على:\n"
        f"• +1 محاولة ألعاب يومية\n"
        f"• فرصة ربح مضاعفة\n\n"
        f"💾 بياناتك محفوظة في الملف!",
        call.message.chat.id,
        call.message.message_id
    )

# =============================================
# ⚡ كل الأوامر الإدارية الأصلية 
# =============================================

@bot.message_handler(commands=['myid'])
def myid(message):
    update_user_activity(message.from_user.id)
    bot.reply_to(message, f"🆔 معرفك: `{message.from_user.id}`", parse_mode='Markdown')

# 💰 إدارة الرصيد
@bot.message_handler(commands=['quickadd'])
def quick_add(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
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

@bot.message_handler(commands=['setbalance'])
def set_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /setbalance [user_id] [amount]")
            return
        
        user_id = int(parts[1])
        amount = float(parts[2])
        
        user = get_user(user_id)
        old_balance = user['balance']
        user['balance'] = amount
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم تعيين رصيد المستخدم {user_id}\n💰 السابق: {old_balance:.1f}\n💰 الجديد: {user['balance']:.1f} USDT")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# 👥 إدارة الإحالات
@bot.message_handler(commands=['setreferrals'])
def set_referrals(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /setreferrals [user_id] [count]")
            return
        
        user_id = int(parts[1])
        count = int(parts[2])
        
        user = get_user(user_id)
        old_count = user['referrals_count']
        user['referrals_count'] = count
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم تعيين إحالات المستخدم {user_id}\n👥 السابق: {old_count}\n👥 الجديد: {user['referrals_count']}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['addreferral'])
def add_referral(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ استخدم: /addreferral [user_id]")
            return
        
        user_id = int(parts[1])
        
        user = get_user(user_id)
        user['referrals_count'] += 1
        user['referrals_new'] += 1
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم إضافة إحالة للمستخدم {user_id}\n👥 الإحالات الجديدة: {user['referrals_new']}\n👥 الإجمالي: {user['referrals_count']}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# 🎯 إدارة المحاولات
@bot.message_handler(commands=['setattempts'])
def set_attempts(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /setattempts [user_id] [attempts]")
            return
        
        user_id = int(parts[1])
        attempts = int(parts[2])
        
        user = get_user(user_id)
        old_attempts = user['games_played_today']
        user['games_played_today'] = attempts
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم تعيين محاولات المستخدم {user_id}\n🎯 السابق: {old_attempts}\n🎯 الجديد: {user['games_played_today']}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['resetattempts'])
def reset_attempts(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ استخدم: /resetattempts [user_id]")
            return
        
        user_id = int(parts[1])
        
        user = get_user(user_id)
        user['games_played_today'] = 0
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم إعادة تعيين محاولات المستخدم {user_id}\n🎯 الآن لديه 0 محاولات مستخدمة")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['addattempts'])
def add_attempts(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /addattempts [user_id] [count]")
            return
        
        user_id = int(parts[1])
        count = int(parts[2])
        
        user = get_user(user_id)
        user['referrals_new'] += count
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم إضافة {count} محاولة للمستخدم {user_id}\n🎯 المحاولات الإضافية: {user['referrals_new']}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# 💳 إدارة الإيداعات
@bot.message_handler(commands=['setdeposits'])
def set_deposits(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /setdeposits [user_id] [amount]")
            return
        
        user_id = int(parts[1])
        amount = float(parts[2])
        
        user = get_user(user_id)
        old_deposits = user['total_deposits']
        user['total_deposits'] = amount
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم تعيين إيداعات المستخدم {user_id}\n💳 السابق: {old_deposits:.1f}\n💳 الجديد: {user['total_deposits']:.1f} USDT")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['adddeposit'])
def add_deposit(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /adddeposit [user_id] [amount]")
            return
        
        user_id = int(parts[1])
        amount = float(parts[2])
        
        user = get_user(user_id)
        user['total_deposits'] += amount
        user['balance'] += amount
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم إضافة إيداع للمستخدم {user_id}\n💳 المبلغ: {amount:.1f} USDT\n💰 الرصيد الجديد: {user['balance']:.1f} USDT")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# 💎 إدارة VIP
@bot.message_handler(commands=['setvip'])
def set_vip(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
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

# 📊 عرض البيانات
@bot.message_handler(commands=['userinfo'])
def user_info(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
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
🎯 المحاولات: {user['games_played_today']}/{total_attempts} (متبقي: {remaining_attempts})
💎 VIP: {get_vip_level_name(user['vip_level'])}
🎮 الألعاب: {user['total_games_played']}
💳 الإيداعات: {user['total_deposits']:.1f} USDT
🏆 الأرباح: {user['total_earned']:.1f} USDT
📅 مسجل منذ: {user['registration_date']}
🕒 آخر نشاط: {last_active}"""
        
        bot.reply_to(message, info_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['listusers'])
def list_users(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
        users_data = load_users()
        users = list(users_data.values())
        
        if not users:
            bot.reply_to(message, "❌ لا يوجد مستخدمين في قاعدة البيانات")
            return
        
        users_list = "📊 قائمة المستخدمين:\n\n"
        for i, user in enumerate(users[:15], 1):
            users_list += f"{i}. {user['first_name']} - {user['user_id']} - {user['balance']:.1f} USDT - {user['referrals_count']} إحالة\n"
        
        if len(users) > 15:
            users_list += f"\n📎 وإجمالي {len(users)} مستخدم"
        
        bot.reply_to(message, users_list)
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    try:
        users_data = load_users()
        users = list(users_data.values())
        
        total_balance = sum(user['balance'] for user in users)
        total_referrals = sum(user['referrals_count'] for user in users)
        total_deposits = sum(user['total_deposits'] for user in users)
        active_users = sum(1 for user in users if user['balance'] > 0 or user['games_played_today'] > 0)
        
        # إحصائيات VIP
        vip_counts = {0: 0, 1: 0, 2: 0, 3: 0}
        for user in users:
            vip_level = user.get('vip_level', 0)
            vip_counts[vip_level] = vip_counts.get(vip_level, 0) + 1
        
        stats_text = f"""
📈 إحصائيات البوت:

👥 إجمالي المستخدمين: {len(users)}
👤 المستخدمين النشطين: {active_users}
💰 إجمالي الرصيد: {total_balance:.1f} USDT
👥 إجمالي الإحالات: {total_referrals}
💳 إجمالي الإيداعات: {total_deposits:.1f} USDT
🎯 مستخدمين بلعبوا اليوم: {sum(1 for user in users if user['games_played_today'] > 0)}

💎 إحصائيات VIP:
🟢 مبتدئ: {vip_counts[0]}
🟢 برونز: {vip_counts[1]}  
🔵 سيلفر: {vip_counts[2]}
🟡 جولد: {vip_counts[3]}"""
        
        bot.reply_to(message, stats_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['adminhelp'])
def admin_help(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    update_user_activity(message.from_user.id)
    
    help_text = """
🛠️ الأوامر الإدارية:

💰 إدارة الرصيد:
/quickadd [user_id] [amount] - إضافة رصيد
/setbalance [user_id] [amount] - تعيين رصيد محدد

👥 إدارة الإحالات:
/setreferrals [user_id] [count] - تعيين عدد الإحالات
/addreferral [user_id] - إضافة إحالة واحدة

🎯 إدارة المحاولات:
/setattempts [user_id] [attempts] - تعيين محاولات الألعاب
/resetattempts [user_id] - إعادة تعيين المحاولات
/addattempts [user_id] [count] - إضافة محاولات

💳 إدارة الإيداعات:
/setdeposits [user_id] [amount] - تعيين إجمالي الإيداعات
/adddeposit [user_id] [amount] - إضافة إيداع

📊 عرض البيانات:
/userinfo [user_id] - معلومات كاملة عن المستخدم
/listusers - قائمة جميع المستخدمين
/stats - إحصائيات البوت

💎 إدارة VIP:
/setvip [user_id] [level] - تعيين مستوى VIP

🔰 أوامر عامة:
/start - الملف الشخصي
/myid - عرض الآيدي

💾 التخزين: ملف JSON
"""
    
    bot.reply_to(message, help_text)

print("🔄 Starting bot...")
print("💾 Database: JSON File (Permanent Storage)")
print("🎮 Games: Slot & Dice (3 attempts + referrals)")
print("💎 VIP Services: Bronze, Silver, Gold")
print("✅ Bot is running and ready!")
print("🛠️ All admin commands loaded!")

if __name__ == "__main__":
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Bot error: {e}")
