import os
import telebot
import sqlite3
import threading
from flask import Flask
import logging
import time
from datetime import datetime

# ✅ تفعيل السجلات المفصلة
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 50)
print("🔍 بدء تشخيص البوت...")
print("=" * 50)

# فحص BOT_TOKEN
BOT_TOKEN = os.environ.get('BOT_TOKEN')
print(f"🔑 BOT_TOKEN موجود: {'✅ نعم' if BOT_TOKEN else '❌ لا'}")
if BOT_TOKEN:
    print(f"🔑 BOT_TOKEN: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
else:
    print("❌ خطأ: BOT_TOKEN غير موجود في environment variables!")
    print("💡 تأكد من إضافة BOT_TOKEN في Railway → Settings → Variables")
    exit(1)

# ======================
# 🗄️ نظام SQLite المبسط
# ======================

DB_FILE = '/tmp/usdt_bot.db' if 'RAILWAY_ENVIRONMENT' in os.environ else 'usdt_bot.db'
db_lock = threading.Lock()

def init_database():
    """تهيئة قاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0.75,
                registration_date TEXT,
                last_activity TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        print(f"✅ تم تهيئة قاعدة البيانات SQLite في: {DB_FILE}")
        return True
    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        return False

def get_user(user_id):
    """جلب أو إنشاء مستخدم"""
    with db_lock:
        try:
            conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
            user_data = cursor.fetchone()
            
            if user_data:
                user_dict = dict(user_data)
                conn.close()
                return user_dict
            else:
                # إنشاء مستخدم جديد
                user_dict = {
                    'user_id': str(user_id),
                    'username': "",
                    'first_name': "",
                    'balance': 0.75,
                    'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'last_activity': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, balance, registration_date, last_activity)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_dict['user_id'], user_dict['username'], user_dict['first_name'],
                    user_dict['balance'], user_dict['registration_date'], user_dict['last_activity']
                ))
                
                conn.commit()
                conn.close()
                print(f"✅ تم إنشاء مستخدم جديد: {user_id}")
                return user_dict
                
        except Exception as e:
            print(f"❌ خطأ في جلب بيانات المستخدم: {e}")
            return None

def update_user_activity(user_id, first_name="", username=""):
    """تحديث نشاط المستخدم"""
    with db_lock:
        try:
            conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users 
                SET first_name = ?, username = ?, last_activity = ?, balance = balance + 0.1
                WHERE user_id = ?
            """, (first_name, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), str(user_id)))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ خطأ في تحديث نشاط المستخدم: {e}")
            return False

def get_user_stats(user_id):
    """جلب إحصائيات المستخدم"""
    user = get_user(user_id)
    if user:
        return f"💰 رصيدك: {user['balance']:.2f} USDT\n📅 مسجل منذ: {user['registration_date']}"
    return "❌ لا توجد بيانات"

# ======================
# 🔧 استمرارية البوت
# ======================

# إنشاء البوت
try:
    bot = telebot.TeleBot(BOT_TOKEN)
    print("✅ تم إنشاء كائن البوت بنجاح")
except Exception as e:
    print(f"❌ فشل في إنشاء البوت: {e}")
    exit(1)

# تهيئة قاعدة البيانات
if not init_database():
    print("⚠️  تم المتابعة بدون قاعدة البيانات")

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 البوت شغال! أرسل /start للبوت"

@app.route('/health')
def health():
    return "✅ OK", 200

# ======================
# 🎯 معالجة الرسائل
# ======================

@bot.message_handler(commands=['start', 'profile'])
def handle_start(message):
    user_info = f"{message.from_user.first_name} (ID: {message.from_user.id})"
    print(f"📩 استلام /start من {user_info}")
    
    try:
        # تحديث بيانات المستخدم
        update_user_activity(
            message.from_user.id,
            message.from_user.first_name,
            message.from_user.username or ""
        )
        
        # جلب بيانات المستخدم
        user_stats = get_user_stats(message.from_user.id)
        
        response = f"مرحباً {message.from_user.first_name}! 👋\n\n"
        response += "🎯 نظام USDT الجديد\n\n"
        response += f"{user_stats}\n\n"
        response += "💎 المزايا:\n"
        response += "• رصيد بداية: 0.75 USDT\n"
        response += "• مكافأة نشاط: 0.10 USDT\n"
        response += "• ألعاب ربحية قريباً\n\n"
        response += "📊 للإحصائيات: /stats"
        
        bot.send_message(message.chat.id, response)
        print(f"✅ تم الرد على {user_info}")
        
    except Exception as e:
        print(f"❌ فشل في معالجة /start: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ، يرجى المحاولة لاحقاً")

@bot.message_handler(commands=['stats'])
def handle_stats(message):
    try:
        user_stats = get_user_stats(message.from_user.id)
        bot.send_message(message.chat.id, f"📊 إحصائياتك:\n\n{user_stats}")
    except Exception as e:
        print(f"❌ خطأ في /stats: {e}")

@bot.message_handler(commands=['balance'])
def handle_balance(message):
    try:
        user = get_user(message.from_user.id)
        if user:
            bot.send_message(message.chat.id, f"💰 رصيدك: {user['balance']:.2f} USDT")
        else:
            bot.send_message(message.chat.id, "❌ لا توجد بيانات")
    except Exception as e:
        print(f"❌ خطأ في /balance: {e}")

# معالجة الرسائل العادية
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if message.text.startswith('/'):
        return  # تجاهل الأوامر الأخرى
        
    user_info = f"{message.from_user.first_name} (ID: {message.from_user.id})"
    print(f"📩 رسالة عادية من {user_info}: {message.text}")
    
    try:
        update_user_activity(message.from_user.id)
        bot.send_message(message.chat.id, "💬 شكراً على رسالتك! استخدم /start للبدء")
    except Exception as e:
        print(f"❌ فشل في معالجة الرسالة: {e}")

def run_bot():
    print("🚀 جاري تشغيل البوت...")
    try:
        bot.polling(
            none_stop=True,
            timeout=30,
            long_polling_timeout=20
        )
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
        print("🔄 إعادة المحاولة بعد 10 ثواني...")
        time.sleep(10)
        run_bot()

if __name__ == "__main__":
    print("🎯 بدء التشغيل...")
    run_bot()
