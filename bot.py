import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from supabase import create_client

BOT_TOKEN = os.environ.get('BOT_TOKEN')
SUPABASE_URL = "https://vgkwwjzkngkobhmvfeio.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZna3d3anprbmdrb2JobXZmZWlvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA2MTYzMzQsImV4cCI6MjA3NjE5MjMzNH0.rcBwsylvtKGI4FroTc4lpJtHMfMaZ_emEXJyBv_9YZM"

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    exit(1)

print(f"✅ Token loaded: {BOT_TOKEN[:10]}...")

bot = telebot.TeleBot(BOT_TOKEN)
ADMIN_IDS = [8400225549]

# 🔧 قاعدة بيانات Supabase
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Connected to Supabase Database!")
except Exception as e:
    print(f"❌ Supabase connection failed: {e}")
    supabase = None

def get_user(user_id):
    user_id_str = str(user_id)
    
    # جرب Supabase أولاً
    if supabase:
        try:
            response = supabase.table('users').select('*').eq('user_id', user_id_str).execute()
            if response.data and len(response.data) > 0:
                print(f"✅ Loaded user {user_id} from Supabase")
                return response.data[0]
        except Exception as e:
            print(f"❌ Error fetching from Supabase: {e}")
    
    # البيانات الافتراضية إذا ما في اتصال أو ما في مستخدم
    user_data = {
        'user_id': user_id_str,
        'username': "",
        'first_name': "",
        'balance': 0.0,
        'referrals_count': 0,
        'games_played_today': 0,
        'total_games_played': 0,
        'total_earned': 0.0,
        'total_deposits': 0.0,
        'vip_level': 0,
        'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_activity': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # حفظ في Supabase إذا متاح
    if supabase:
        try:
            supabase.table('users').insert(user_data).execute()
            print(f"✅ Created new user {user_id} in Supabase")
        except Exception as e:
            print(f"❌ Error creating user in Supabase: {e}")
    
    return user_data

def save_user(user_data):
    if supabase:
        try:
            # تحديث البيانات في Supabase
            supabase.table('users').update({
                'username': user_data['username'],
                'first_name': user_data['first_name'],
                'balance': user_data['balance'],
                'referrals_count': user_data['referrals_count'],
                'games_played_today': user_data['games_played_today'],
                'total_games_played': user_data['total_games_played'],
                'total_earned': user_data['total_earned'],
                'total_deposits': user_data['total_deposits'],
                'vip_level': user_data['vip_level'],
                'last_activity': user_data['last_activity']
            }).eq('user_id', user_data['user_id']).execute()
            
            print(f"💾 Saved user {user_data['user_id']} to Supabase")
            return True
        except Exception as e:
            print(f"❌ Error saving to Supabase: {e}")
            return False
    return False

def update_user_activity(user_id):
    user = get_user(user_id)
    user['last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_user(user)

# 🎯 الأوامر للجميع
@bot.message_handler(commands=['start'])
def start_command(message):
    user = get_user(message.from_user.id)
    user['first_name'] = message.from_user.first_name or ""
    user['username'] = message.from_user.username or ""
    update_user_activity(message.from_user.id)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral"))
    keyboard.add(InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4"))
    
    bot.send_message(
        message.chat.id,
        f"أهلاً {message.from_user.first_name}! 👋\n💰 رصيدك: {user['balance']:.1f} USDT\n💾 البيانات: دائمة\nاختر من الأزرار:",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['myid'])
def myid(message):
    update_user_activity(message.from_user.id)
    bot.reply_to(message, f"🆔 معرفك: `{message.from_user.id}`", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    update_user_activity(call.from_user.id)
    
    if call.data == "referral":
        referral_link = f"https://t.me/{bot.get_me().username}?start=ref{call.from_user.id}"
        bot.edit_message_text(
            f"🎯 رابطك الخاص:\n`{referral_link}`\n\n💾 بياناتك محفوظة للأبد!",
            call.message.chat.id,
            call.message.message_id
        )

# 💰 إدارة الرصيد (للمشرفين)
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
        
        bot.reply_to(message, f"✅ تم إضافة {amount} USDT للمستخدم {user_id}\n💰 الرصيد الجديد: {user['balance']:.1f} USDT\n💾 تم الحفظ في قاعدة البيانات")
        
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
        
        bot.reply_to(message, f"✅ تم تعيين رصيد المستخدم {user_id}\n💰 السابق: {old_balance:.1f}\n💰 الجديد: {user['balance']:.1f} USDT\n💾 تم الحفظ في قاعدة البيانات")
        
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
        
        bot.reply_to(message, f"✅ تم تعيين إحالات المستخدم {user_id}\n👥 السابق: {old_count}\n👥 الجديد: {user['referrals_count']}\n💾 تم الحفظ في قاعدة البيانات")
        
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
        
        bot.reply_to(message, f"✅ تم تعيين محاولات المستخدم {user_id}\n🎯 السابق: {old_attempts}/3\n🎯 الجديد: {user['games_played_today']}/3\n💾 تم الحفظ في قاعدة البيانات")
        
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
        
        bot.reply_to(message, f"✅ تم إعادة تعيين محاولات المستخدم {user_id}\n🎯 الآن لديه 3/3 محاولات\n💾 تم الحفظ في قاعدة البيانات")
        
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
        
        remaining_attempts = 3 - user['games_played_today']
        last_active = user.get('last_activity', 'غير معروف')
        
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
🏆 الأرباح: {user['total_earned']:.1f} USDT
📅 مسجل منذ: {user['registration_date']}
🕒 آخر نشاط: {last_active}
💾 التخزين: قاعدة بيانات دائمة"""
        
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
        if supabase:
            response = supabase.table('users').select('*').execute()
            users = response.data
        else:
            users = []
        
        if not users:
            bot.reply_to(message, "❌ لا يوجد مستخدمين في قاعدة البيانات")
            return
        
        users_list = "📊 قائمة المستخدمين:\n\n"
        for i, user in enumerate(users[:15], 1):
            users_list += f"{i}. {user['first_name']} - {user['user_id']} - {user['balance']:.1f} USDT - {user['referrals_count']} إحالة\n"
        
        if len(users) > 15:
            users_list += f"\n📎 وإجمالي {len(users)} مستخدم"
        
        users_list += f"\n💾 قاعدة بيانات: Supabase"
        
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
        if supabase:
            response = supabase.table('users').select('*').execute()
            users = response.data
        else:
            users = []
        
        total_balance = sum(user['balance'] for user in users)
        total_referrals = sum(user['referrals_count'] for user in users)
        total_deposits = sum(user['total_deposits'] for user in users)
        active_users = sum(1 for user in users if user['balance'] > 0 or user['games_played_today'] > 0)
        
        stats_text = f"""
📈 إحصائيات البوت:

👥 إجمالي المستخدمين: {len(users)}
👤 المستخدمين النشطين: {active_users}
💰 إجمالي الرصيد: {total_balance:.1f} USDT
👥 إجمالي الإحالات: {total_referrals}
💳 إجمالي الإيداعات: {total_deposits:.1f} USDT
🎯 مستخدمين بلعبوا اليوم: {sum(1 for user in users if user['games_played_today'] > 0)}
💾 قاعدة بيانات: Supabase (دائمة)"""
        
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

🎯 إدارة المحاولات:
/setattempts [user_id] [attempts] - تعيين محاولات الألعاب
/resetattempts [user_id] - إعادة تعيين المحاولات

📊 عرض البيانات:
/userinfo [user_id] - معلومات كاملة عن المستخدم
/listusers - قائمة جميع المستخدمين
/stats - إحصائيات البوت

🔰 أوامر عامة:
/start - القائمة الرئيسية
/myid - عرض الآيدي

💾 التخزين: قاعدة بيانات دائمة (Supabase)
"""
    
    bot.reply_to(message, help_text)

print("🔄 Starting bot...")
print("💾 Database: Supabase (Permanent Storage)")
print("✅ Bot is running and ready!")
print("🛠️ All admin commands loaded!")
bot.infinity_polling()

# =============================================
# ⚡ كود تشغيل السيرفر لـ Render
# =============================================
if __name__ == "__main__":
    import os
    from flask import Flask
    
    # إنشاء تطبيق Flask بورت إضافي
    web_app = Flask(__name__)
    
    @web_app.route('/')
    def home():
        return "🤖 Bot is running!"
    
    # تشغيل البوت وتطبيق الويب
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)
