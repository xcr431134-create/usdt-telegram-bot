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
                vip_level INTEGER DEFAULT 0,
                registration_date TEXT
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
                    'vip_level': user_data[5]
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
                    'vip_level': 0,
                    'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, balance, referral_count, vip_level, registration_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_user['user_id'], new_user['username'], new_user['first_name'],
                    new_user['balance'], new_user['referral_count'], new_user['vip_level'],
                    new_user['registration_date']
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

# 🎯 الدالة الجديدة والمحسنة للـ Start
@bot.message_handler(commands=['start', 'بدء', 'البدء'])
def handle_start_new(message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name or "مستخدم"
        username = message.from_user.username or ""
        
        print(f"🎯 استلام /start من {user_id} - {first_name}")
        
        # الحصول على بيانات المستخدم أو إنشاؤه
        user_data = get_user(user_id)
        
        if user_data:
            # تحديث بيانات المستخدم إذا كانت موجودة
            update_user(
                user_id,
                first_name=first_name,
                username=username
            )
        else:
            print(f"❌ فشل في إنشاء/جلب المستخدم {user_id}")
        
        # إنشاء واجهة المستخدم الرئيسية
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎮 ألعاب الربح", callback_data="games"),
            InlineKeyboardButton("💎 العضويات VIP", callback_data="vip_services"),
            InlineKeyboardButton("👥 نظام الإحالات", callback_data="referral"),
            InlineKeyboardButton("💰 سحب الأرباح", callback_data="withdraw"),
            InlineKeyboardButton("📊 الملف الشخصي", callback_data="profile")
        )
        
        # رسالة الترحيب المحسنة
        welcome_text = f"""
🎊 **مرحباً بك في بوت USDT!** 🎊

👤 **المستخدم:** {first_name}
🆔 **الآيدي:** `{user_id}`
💰 **الرصيد:** {user_data['balance'] if user_data else '0.75'} USDT
🏆 **المستوى:** {VIP_LEVELS[user_data['vip_level'] if user_data else 0]['name']}

🎯 **مميزات البوت:**
• 🎮 ألعاب بربح حقيقي
• 💎 عضويات VIP مميزة  
• 👥 نظام إحالات مربح
• 💰 سحب أرباح بسهولة

🚀 **اختر من القائمة:**
        """
        
        bot.send_message(
            user_id,
            welcome_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        print(f"✅ تم إرسال الترحيب لـ {user_id}")
        
    except Exception as e:
        print(f"❌ خطأ في الدالة الجديدة: {e}")
        try:
            bot.send_message(
                message.chat.id,
                "🎯 أهلاً بك! استخدم الأزرار للبدء 🚀",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 ابدأ الآن", callback_data="start_main")]
                ])
            )
        except:
            pass

# 🆔 دالة الـ myid (شغالة)
@bot.message_handler(commands=['myid'])
def handle_myid(message):
    try:
        user_id = message.from_user.id
        bot.reply_to(
            message, 
            f"🆔 **معرفك:** `{user_id}`\n\n"
            f"👤 **الاسم:** {message.from_user.first_name or 'غير معروف'}\n"
            f"📅 **الوقت:** {datetime.now().strftime('%Y-%m-%د %H:%M:%S')}",
            parse_mode='Markdown'
        )
        print(f"✅ تم عرض الآيدي لـ {user_id}")
    except Exception as e:
        print(f"❌ خطأ في /myid: {e}")

# 🎮 معالجة الأزرار
@bot.callback_query_handler(func=lambda call: call.data == "start_main")
def handle_start_button(call):
    try:
        handle_start_new(call.message)
    except Exception as e:
        print(f"❌ خطأ في زر البدء: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "games")
def show_games(call):
    try:
        user = get_user(call.from_user.id)
        vip_info = VIP_LEVELS[user['vip_level']]
        
        games_text = f"""
🎮 **قائمة الألعاب**

🎯 المحاولات المتاحة: {vip_info['max_attempts']}
💰 الربح لكل جولة: 2.5 USDT

اختر اللعبة المناسبة:
        """
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎰 سلوت الحظ", callback_data="game_slot"),
            InlineKeyboardButton("🎲 نرد الرهان", callback_data="game_dice")
        )
        keyboard.add(InlineKeyboardButton("🔙 الرجوع", callback_data="back_main"))
        
        bot.edit_message_text(
            games_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ خطأ في عرض الألعاب: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_to_main(call):
    try:
        handle_start_new(call.message)
    except Exception as e:
        print(f"❌ خطأ في الرجوع: {e}")

# 🎰 لعبة السلوت البسيطة
@bot.callback_query_handler(func=lambda call: call.data == "game_slot")
def play_slot_simple(call):
    try:
        user_id = call.from_user.id
        symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎"]
        result = [random.choice(symbols) for _ in range(3)]
        
        # حساب الربح
        if result[0] == result[1] == result[2]:
            win_amount = 2.5
            win_text = "🎉 ربح كبير! احسنت!"
        elif result[0] == result[1] or result[1] == result[2]:
            win_amount = 1.25
            win_text = "👍 ربح جيد!"
        else:
            win_amount = 0
            win_text = "😞 حاول مرة أخرى"
        
        # تحديث الرصيد
        user = get_user(user_id)
        if user:
            new_balance = user['balance'] + win_amount
            update_user(user_id, balance=new_balance)
        
        game_result = f"""
🎰 **لعبة السلوت**

{' | '.join(result)}

{win_text}
💰 **الربح:** {win_amount:.2f} USDT
💵 **الرصيد الجديد:** {new_balance:.2f} USDT

        """
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🎰 العب مرة أخرى", callback_data="game_slot"))
        keyboard.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main"))
        
        bot.edit_message_text(
            game_result,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    except Exception as e:
        print(f"❌ خطأ في لعبة السلوت: {e}")

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
    print("🎯 نظام البوت الجديد - الإصدار المحسن")
    
    # تشغيل Flask في الخلفية
    def run_flask():
        app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
    
    import threading
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # تشغيل البوت
    run_bot()
