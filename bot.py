import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    exit(1)

print(f"✅ Token loaded: {BOT_TOKEN[:10]}...")

bot = telebot.TeleBot(BOT_TOKEN)

# قاعدة بيانات بسيطة
users_db = {}
ADMIN_IDS = [8400225549]

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {
            'user_id': user_id,
            'username': "",
            'first_name': "",
            'balance': 0.0,
            'referrals_count': 0,
            'games_played_today': 0,
            'total_games_played': 0,
            'total_earned': 0.0,
            'total_deposits': 0.0,
            'vip_level': 0,
            'registration_date': "2024-01-01"
        }
    return users_db[user_id]

# 🔰 الأوامر للجميع
@bot.message_handler(commands=['start'])
def start_command(message):
    user = get_user(message.from_user.id)
    user['first_name'] = message.from_user.first_name or ""
    user['username'] = message.from_user.username or ""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral"))
    keyboard.add(InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4"))
    
    bot.send_message(
        message.chat.id,
        f"أهلاً {message.from_user.first_name}! 👋\n💰 رصيدك: {user['balance']:.1f} USDT\nاختر من الأزرار:",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['myid'])
def myid(message):
    bot.reply_to(message, f"🆔 معرفك: `{message.from_user.id}`", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    if call.data == "referral":
        referral_link = f"https://t.me/{bot.get_me().username}?start=ref{call.from_user.id}"
        bot.edit_message_text(
            f"🎯 رابطك الخاص:\n`{referral_link}`",
            call.message.chat.id,
            call.message.message_id
        )

# 💰 إدارة الرصيد (للمشرفين)
@bot.message_handler(commands=['quickadd'])
def quick_add(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
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
        
        bot.reply_to(message, f"✅ تم إضافة {amount} USDT للمستخدم {user_id}\n💰 الرصيد الجديد: {user['balance']:.1f} USDT")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setbalance'])
def set_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
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
        
        bot.reply_to(message, f"✅ تم تعيين رصيد المستخدم {user_id}\n💰 السابق: {old_balance:.1f}\n💰 الجديد: {user['balance']:.1f} USDT")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# 👥 إدارة الإحالات
@bot.message_handler(commands=['setreferrals'])
def set_referrals(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
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
        
        bot.reply_to(message, f"✅ تم تعيين إحالات المستخدم {user_id}\n👥 السابق: {old_count}\n👥 الجديد: {user['referrals_count']}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['addreferral'])
def add_referral(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ استخدم: /addreferral [user_id]")
            return
        
        user_id = int(parts[1])
        
        user = get_user(user_id)
        user['referrals_count'] += 1
        
        bot.reply_to(message, f"✅ تم إضافة إحالة للمستخدم {user_id}\n👥 الإحالات الجديدة: {user['referrals_count']}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# 🎯 إدارة المحاولات
@bot.message_handler(commands=['setattempts'])
def set_attempts(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
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
        
        bot.reply_to(message, f"✅ تم تعيين محاولات المستخدم {user_id}\n🎯 السابق: {old_attempts}/3\n🎯 الجديد: {user['games_played_today']}/3")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['resetattempts'])
def reset_attempts(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ استخدم: /resetattempts [user_id]")
            return
        
        user_id = int(parts[1])
        
        user = get_user(user_id)
        user['games_played_today'] = 0
        
        bot.reply_to(message, f"✅ تم إعادة تعيين محاولات المستخدم {user_id}\n🎯 الآن لديه 3/3 محاولات")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['addattempts'])
def add_attempts(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /addattempts [user_id] [count]")
            return
        
        user_id = int(parts[1])
        count = int(parts[2])
        
        user = get_user(user_id)
        user['games_played_today'] = max(0, user['games_played_today'] - count)
        
        bot.reply_to(message, f"✅ تم إضافة {count} محاولة للمستخدم {user_id}\n🎯 المحاولات المتبقية: {3 - user['games_played_today']}/3")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# 💳 إدارة الإيداعات
@bot.message_handler(commands=['setdeposits'])
def set_deposits(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
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
        
        bot.reply_to(message, f"✅ تم تعيين إيداعات المستخدم {user_id}\n💳 السابق: {old_deposits:.1f}\n💳 الجديد: {user['total_deposits']:.1f} USDT")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['adddeposit'])
def add_deposit(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /adddeposit [user_id] [amount]")
            return
        
        user_id = int(parts[1])
        amount = float(parts[2])
        
        user = get_user(user_id)
        user['total_deposits'] += amount
        
        bot.reply_to(message, f"✅ تم إضافة إيداع للمستخدم {user_id}\n💳 الإيداعات الجديدة: {user['total_deposits']:.1f} USDT")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# 📊 عرض البيانات
@bot.message_handler(commands=['userinfo'])
def user_info(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ استخدم: /userinfo [user_id]")
            return
        
        user_id = int(parts[1])
        user = get_user(user_id)
        
        remaining_attempts = 3 - user['games_played_today']
        
        info_text = f"""
📊 معلومات المستخدم:

🆔 الآيدي: {user['user_id']}
👤 الاسم: {user['first_name']}
💰 الرصيد: {user['balance']:.1f} USDT
👥 الإحالات: {user['referrals_count']}
🎯 المحاولات: {user['games_played_today']}/3 (متبقي: {remaining_attempts})
💎 VIP: {user['vip_level']}
🎮 الألعاب: {user['total_games_played']}
💳 الإيداعات: {user['total_deposits']:.1f} USDT
🏆 الأرباح: {user['total_earned']:.1f} USDT"""
        
        bot.reply_to(message, info_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['listusers'])
def list_users(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        if len(users_db) == 0:
            bot.reply_to(message, "❌ لا يوجد مستخدمين في قاعدة البيانات")
            return
        
        users_list = "📊 قائمة المستخدمين:\n\n"
        for i, (user_id, user_data) in enumerate(list(users_db.items())[:15], 1):
            users_list += f"{i}. {user_data['first_name']} - {user_id} - {user_data['balance']:.1f} USDT - {user_data['referrals_count']} إحالة\n"
        
        if len(users_db) > 15:
            users_list += f"\n📎 وإجمالي {len(users_db)} مستخدم"
        
        bot.reply_to(message, users_list)
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        total_balance = sum(user['balance'] for user in users_db.values())
        total_referrals = sum(user['referrals_count'] for user in users_db.values())
        total_deposits = sum(user['total_deposits'] for user in users_db.values())
        active_users = sum(1 for user in users_db.values() if user['balance'] > 0 or user['games_played_today'] > 0)
        
        stats_text = f"""
📈 إحصائيات البوت:

👥 إجمالي المستخدمين: {len(users_db)}
👤 المستخدمين النشطين: {active_users}
💰 إجمالي الرصيد: {total_balance:.1f} USDT
👥 إجمالي الإحالات: {total_referrals}
💳 إجمالي الإيداعات: {total_deposits:.1f} USDT
🎯 مستخدمين بلعبوا اليوم: {sum(1 for user in users_db.values() if user['games_played_today'] > 0)}"""
        
        bot.reply_to(message, stats_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# 💎 إدارة VIP
@bot.message_handler(commands=['setvip'])
def set_vip(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /setvip [user_id] [level]")
            return
        
        user_id = int(parts[1])
        level = int(parts[2])
        
        user = get_user(user_id)
        old_level = user['vip_level']
        user['vip_level'] = level
        
        bot.reply_to(message, f"✅ تم تعيين مستوى VIP للمستخدم {user_id}\n💎 السابق: {old_level}\n💎 الجديد: {user['vip_level']}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['adminhelp'])
def admin_help(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
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
/start - القائمة الرئيسية
/myid - عرض الآيدي
"""
    
    bot.reply_to(message, help_text)

print("🔄 Starting bot...")
print("✅ Bot is running and ready!")
print("🛠️ All admin commands loaded!")
bot.infinity_polling()
