import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    exit(1)

print(f"✅ Token loaded: {BOT_TOKEN[:10]}...")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 🔧 قاعدة بيانات مؤقتة
users_db = {}
ADMIN_IDS = [8400225549]  # ضع آيدي المشرف هنا

# 🔧 دوال مساعدة
def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {
            'user_id': user_id,
            'username': "",
            'first_name': "",
            'last_name': "",
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

def save_user(user_data):
    users_db[user_data['user_id']] = user_data
    return True

# 🎯 الأوامر الأساسية
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    print(f"🚀 User {user.id} started the bot")
    
    # إنشاء مستخدم جديد إذا ما موجود
    user_data = get_user(user.id)
    user_data['first_name'] = user.first_name or ""
    user_data['username'] = user.username or ""
    
    keyboard = [
        [InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral")],
        [InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"أهلاً {user.first_name}! 👋\n💰 رصيدك: {user_data['balance']:.1f} USDT\nاختر من الأزرار:",
        reply_markup=reply_markup
    )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.data == "referral":
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start=ref{query.from_user.id}"
        query.edit_message_text(f"🎯 رابطك الخاص:\n`{referral_link}`")

# 🛠️ الأوامر الإدارية
def quick_add_balance(update: Update, context: CallbackContext):
    """إضافة رصيد للمستخدم"""
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 2:
            update.message.reply_text("❌ استخدم: /quickadd [user_id] [amount]")
            return
        
        target_user_id = int(context.args[0])
        amount = float(context.args[1])
        
        user = get_user(target_user_id)
        user['balance'] += amount
        user['total_earned'] += amount
        
        response = f"✅ تم إضافة {amount} USDT للمستخدم {target_user_id}\n💰 الرصيد الجديد: {user['balance']:.1f} USDT"
        update.message.reply_text(response)
        
    except Exception as e:
        update.message.reply_text(f"❌ خطأ: {e}")

def set_balance(update: Update, context: CallbackContext):
    """تعيين رصيد محدد"""
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 2:
            update.message.reply_text("❌ استخدم: /setbalance [user_id] [amount]")
            return
        
        target_user_id = int(context.args[0])
        amount = float(context.args[1])
        
        user = get_user(target_user_id)
        old_balance = user['balance']
        user['balance'] = amount
        
        response = f"✅ تم تعيين رصيد المستخدم {target_user_id}\n💰 الرصيد السابق: {old_balance:.1f} USDT\n💰 الرصيد الجديد: {user['balance']:.1f} USDT"
        update.message.reply_text(response)
        
    except Exception as e:
        update.message.reply_text(f"❌ خطأ: {e}")

def set_referrals(update: Update, context: CallbackContext):
    """تعيين عدد الإحالات"""
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 2:
            update.message.reply_text("❌ استخدم: /setreferrals [user_id] [count]")
            return
        
        target_user_id = int(context.args[0])
        count = int(context.args[1])
        
        user = get_user(target_user_id)
        old_count = user['referrals_count']
        user['referrals_count'] = count
        
        response = f"✅ تم تعيين إحالات المستخدم {target_user_id}\n👥 الإحالات السابقة: {old_count}\n👥 الإحالات الجديدة: {user['referrals_count']}"
        update.message.reply_text(response)
        
    except Exception as e:
        update.message.reply_text(f"❌ خطأ: {e}")

def set_attempts(update: Update, context: CallbackContext):
    """تعيين محاولات الألعاب"""
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 2:
            update.message.reply_text("❌ استخدم: /setattempts [user_id] [attempts]")
            return
        
        target_user_id = int(context.args[0])
        attempts = int(context.args[1])
        
        user = get_user(target_user_id)
        old_attempts = user['games_played_today']
        user['games_played_today'] = attempts
        
        response = f"✅ تم تعيين محاولات المستخدم {target_user_id}\n🎯 المحاولات السابقة: {old_attempts}/3\n🎯 المحاولات الجديدة: {user['games_played_today']}/3"
        update.message.reply_text(response)
        
    except Exception as e:
        update.message.reply_text(f"❌ خطأ: {e}")

def reset_attempts(update: Update, context: CallbackContext):
    """إعادة تعيين المحاولات"""
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 1:
            update.message.reply_text("❌ استخدم: /resetattempts [user_id]")
            return
        
        target_user_id = int(context.args[0])
        
        user = get_user(target_user_id)
        user['games_played_today'] = 0
        
        response = f"✅ تم إعادة تعيين محاولات المستخدم {target_user_id}\n🎯 الآن لديه 3/3 محاولات"
        update.message.reply_text(response)
        
    except Exception as e:
        update.message.reply_text(f"❌ خطأ: {e}")

def user_info(update: Update, context: CallbackContext):
    """معلومات المستخدم"""
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 1:
            update.message.reply_text("❌ استخدم: /userinfo [user_id]")
            return
        
        user_id = int(context.args[0])
        user = get_user(user_id)
        
        info_text = f"""
📊 معلومات المستخدم:

🆔 الآيدي: {user['user_id']}
👤 الاسم: {user['first_name']}
💰 الرصيد: {user['balance']:.1f} USDT
👥 الإحالات: {user['referrals_count']}
🎯 المحاولات: {user['games_played_today']}/3
💎 VIP: {user['vip_level']}
🎮 الألعاب: {user['total_games_played']}
💳 الإيداعات: {user['total_deposits']:.1f} USDT
🏆 الأرباح: {user['total_earned']:.1f} USDT"""
        
        update.message.reply_text(info_text)
        
    except Exception as e:
        update.message.reply_text(f"❌ خطأ: {e}")

def list_users(update: Update, context: CallbackContext):
    """قائمة المستخدمين"""
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(users_db) == 0:
            update.message.reply_text("❌ لا يوجد مستخدمين في قاعدة البيانات")
            return
        
        users_list = "📊 قائمة المستخدمين:\n\n"
        for i, (user_id, user_data) in enumerate(list(users_db.items())[:15], 1):
            users_list += f"{i}. {user_data['first_name']} - {user_id} - {user_data['balance']:.1f} USDT - {user_data['referrals_count']} إحالة\n"
        
        if len(users_db) > 15:
            users_list += f"\n📎 وإجمالي {len(users_db)} مستخدم"
        
        update.message.reply_text(users_list)
        
    except Exception as e:
        update.message.reply_text(f"❌ خطأ: {e}")

def admin_help(update: Update, context: CallbackContext):
    """مساعدة الأوامر الإدارية"""
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    help_text = """
🛠️ الأوامر الإدارية:

💰 إدارة الرصيد:
/quickadd [user_id] [amount] - إضافة رصيد
/setbalance [user_id] [amount] - تعيين رصيد محدد

👥 إدارة الإحالات:
/setreferrals [user_id] [count] - تعيين عدد الإحالات

🎯 إدارة المحاولات:
/setattempts [user_id] [attempts] - تعيين محاولات الألعاب
/resetattempts [user_id] - إعادة تعيين المحاولات

📊 عرض البيانات:
/userinfo [user_id] - معلومات المستخدم
/listusers - قائمة جميع المستخدمين
/adminhelp - مساعدة الأوامر الإدارية
"""
    
    update.message.reply_text(help_text)

def main():
    try:
        print("🔄 Starting bot...")
        updater = Updater(BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # الأوامر الأساسية
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CallbackQueryHandler(button_handler))
        
        # الأوامر الإدارية
        dispatcher.add_handler(CommandHandler("quickadd", quick_add_balance))
        dispatcher.add_handler(CommandHandler("setbalance", set_balance))
        dispatcher.add_handler(CommandHandler("setreferrals", set_referrals))
        dispatcher.add_handler(CommandHandler("setattempts", set_attempts))
        dispatcher.add_handler(CommandHandler("resetattempts", reset_attempts))
        dispatcher.add_handler(CommandHandler("userinfo", user_info))
        dispatcher.add_handler(CommandHandler("listusers", list_users))
        dispatcher.add_handler(CommandHandler("adminhelp", admin_help))
        
        print("✅ Bot is running and ready to receive messages...")
        print("🛠️ Admin commands loaded:")
        print("   /quickadd, /setbalance, /setreferrals, /setattempts")
        print("   /resetattempts, /userinfo, /listusers, /adminhelp")
        
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == '__main__':
    main()
