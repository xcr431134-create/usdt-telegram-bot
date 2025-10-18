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

if not BOT_TOKEN:
    print("❌ خطأ: BOT_TOKEN غير موجود في environment variables!")
    exit(1)

# ======================
# 🗄️ نظام SQLite معدل لـ Railway
# ======================

# استخدام المسار الحالي بدلاً من /tmp
DB_FILE = os.path.join(os.getcwd(), 'usdt_bot.db')
db_lock = threading.Lock()

def init_database():
    """تهيئة قاعدة البيانات مع معالجة محسنة للصلاحيات"""
    try:
        print(f"📁 محاولة إنشاء قاعدة بيانات في: {DB_FILE}")
        
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        # إنشاء الجدول
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
        print(f"✅ تم تهيئة قاعدة البيانات بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        print("🔄 المتابعة بدون قاعدة البيانات...")
        return False

def get_db_connection():
    """إنشاء اتصال آمن بقاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ فشل في الاتصال بقاعدة البيانات: {e}")
        return None

def get_user(user_id):
    """جلب أو إنشاء مستخدم"""
    with db_lock:
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                return None
                
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
            user_data = cursor.fetchone()
            
            if user_data:
                user_dict = dict(user_data)
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
                print(f"✅ تم إنشاء مستخدم جديد: {user_id}")
                return user_dict
                
        except Exception as e:
            print(f"❌ خطأ في جلب بيانات المستخدم: {e}")
            return None
        finally:
            if conn:
                conn.close()

def update_user_activity(user_id, first_name="", username=""):
    """تحديث نشاط المستخدم"""
    with db_lock:
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            
            # التحقق إذا المستخدم موجود
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
            if cursor.fetchone():
                # تحديث المستخدم الموجود
                cursor.execute("""
                    UPDATE users 
                    SET first_name = ?, username = ?, last_activity = ?, balance = balance + 0.1
                    WHERE user_id = ?
                """, (first_name, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), str(user_id)))
            else:
                # إنشاء مستخدم جديد
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, balance, registration_date, last_activity)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(user_id), username, first_name, 0.75,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ خطأ في تحديث نشاط المستخدم: {e}")
            return False
        finally:
            if conn:
                conn.close()

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
        success = update_user_activity(
            message.from_user.id,
            message.from_user.first_name,
            message.from_user.username or ""
        )
        
        if success:
            user_stats = get_user_stats(message.from_user.id)
            
            response = f"مرحباً {message.from_user.first_name}! 👋\n\n"
            response += "🎯 نظام USDT الجديد\n\n"
            response += f"{user_stats}\n\n"
            response += "💎 المزايا:\n"
            response += "• رصيد بداية: 0.75 USDT\n"
            response += "• مكافأة نشاط: 0.10 USDT\n"
            response += "• ألعاب ربحية قريباً\n\n"
            response += "📊 للإحصائيات: /stats"
        else:
            response = f"مرحباً {message.from_user.first_name}! 👋\n\n"
            response += "🎯 نظام USDT الجديد\n\n"
            response += "💰 رصيدك: 0.75 USDT\n"
            response += "📅 وقت التسجيل: الآن\n\n"
            response += "💎 نظام التخزين قيد التطوير..."
        
        bot.send_message(message.chat.id, response)
        print(f"✅ تم الرد على {user_info}")
        
    except Exception as e:
        print(f"❌ فشل في معالجة /start: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ، يرجى المحاولة لاحقاً")

@bot.message_handler(commands=['stats', 'balance'])
def handle_stats(message):
    try:
        user_stats = get_user_stats(message.from_user.id)
        bot.send_message(message.chat.id, f"📊 إحصائياتك:\n\n{user_stats}")
    except Exception as e:
        print(f"❌ خطأ في /stats: {e}")
        bot.send_message(message.chat.id, "💰 رصيدك: 0.75 USDT\n📊 النظام قيد التطوير...")

@bot.message_handler(commands=['admin'])
def handle_admin(message):
    """أمر للمشرفين فقط"""
    if str(message.from_user.id) not in ['ADMIN_USER_ID_HERE']:  # ضع ID المشرف هنا
        return
    
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users")
            user_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT SUM(balance) as total FROM users")
            total_balance = cursor.fetchone()['total'] or 0
            
            conn.close()
            
            admin_msg = f"👑 إحصائيات المشرف:\n\n"
            admin_msg += f"👥 عدد المستخدمين: {user_count}\n"
            admin_msg += f"💰 إجمالي الرصيد: {total_balance:.2f} USDT\n"
            admin_msg += f"📊 متوسط الرصيد: {total_balance/user_count:.2f} USDT" if user_count > 0 else "📊 متوسط الرصيد: 0"
            
            bot.send_message(message.chat.id, admin_msg)
    except Exception as e:
        print(f"❌ خطأ في /admin: {e}")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if message.text.startswith('/'):
        return
        
    user_info = f"{message.from_user.first_name} (ID: {message.from_user.id})"
    print(f"📩 رسالة عادية من {user_info}: {message.text}")
    
    try:
        update_user_activity(message.from_user.id)
        bot.send_message(message.chat.id, "💬 شكراً على رسالتك! استخدم /start للبدء")
    except Exception as e:
        print(f"❌ فشل في معالجة الرسالة: {e}")

def run_bot():
    print("🚀 جاري تشغيل البوت...")
    
    # تهيئة قاعدة البيانات
    if not init_database():
        print("⚠️  تم المتابعة بدون قاعدة البيانات")
    
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
