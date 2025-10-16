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
            'balance': 0.0,
            'referrals_count': 0,
            'games_played_today': 0
        }
    return users_db[user_id]

@bot.message_handler(commands=['start'])
def start_command(message):
    user = get_user(message.from_user.id)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral"))
    keyboard.add(InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4"))
    
    bot.send_message(
        message.chat.id,
        f"أهلاً {message.from_user.first_name}! 👋\n💰 رصيدك: {user['balance']:.1f} USDT\nاختر من الأزرار:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    if call.data == "referral":
        referral_link = f"https://t.me/{bot.get_me().username}?start=ref{call.from_user.id}"
        bot.edit_message_text(
            f"🎯 رابطك الخاص:\n`{referral_link}`",
            call.message.chat.id,
            call.message.message_id
        )

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

@bot.message_handler(commands=['myid'])
def myid(message):
    bot.reply_to(message, f"🆔 معرفك: `{message.from_user.id}`", parse_mode='Markdown')

@bot.message_handler(commands=['adminhelp'])
def admin_help(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    help_text = """
🛠️ الأوامر الإدارية:

/quickadd [user_id] [amount] - إضافة رصيد
/setbalance [user_id] [amount] - تعيين رصيد
/myid - عرض الآيدي
"""
    bot.reply_to(message, help_text)

print("🔄 Starting bot...")
print("✅ Bot is running and ready!")
bot.infinity_polling()
