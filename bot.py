import os
import telebot
import random
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import time
import requests
from flask import Flask
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import sys

# ✅ تمكين السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 📡 Flask Server
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 USDT Telegram Bot is Running!"

@app.route('/health')
def health_check():
    return "✅ OK", 200

# 🔧 الإعدادات
BOT_TOKEN = "7973697789:AAFXfYXTgYaTAF1j7IGhp2kiv-kxrN1uImk"
DATABASE_URL = "postgresql://bot_user:k6xr1HgqhKV4l1B5lpWnxPKxgFFHe5OC@dpg-d3peu8ggjchc73ah3nc0-a.oregon-postgres.render.com/bot_database_sf0a"
ADMIN_IDS = [8400225549]

bot = telebot.TeleBot(BOT_TOKEN)
print("✅ تم تحميل البوت بنجاح!")

# ======================
# 🗄️ نظام قاعدة البيانات
# ======================

def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات"""
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        print("✅ تم الاتصال بقاعدة البيانات!")
        return conn
    except Exception as e:
        print(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
        return None

def init_database():
    """تهيئة الجداول"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance REAL DEFAULT 0.75,
                    referrals_count INTEGER DEFAULT 0,
                    referrals_new INTEGER DEFAULT 0,
                    games_played_today INTEGER DEFAULT 0,
                    total_games_played INTEGER DEFAULT 0,
                    total_earned REAL DEFAULT 0.75,
                    total_deposits REAL DEFAULT 0.0,
                    vip_level INTEGER DEFAULT 0,
                    registration_date TEXT,
                    last_activity TEXT,
                    last_reset_date TEXT,
                    withdrawal_address TEXT,
                    registration_days INTEGER DEFAULT 0
                )
            """)
            conn.commit()
            print("✅ تم تهيئة قاعدة البيانات!")
            return True
            
    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_user(user_id):
    """جلب بيانات المستخدم"""
    try:
        conn = get_db_connection()
        if not conn:
            return create_default_user(user_id)
            
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (str(user_id),))
            user_data = cur.fetchone()
            
            if user_data:
                user_dict = dict(user_data)
                return user_dict
            else:
                return create_default_user(user_id)
                
    except Exception as e:
        print(f"❌ خطأ في جلب بيانات المستخدم: {e}")
        return create_default_user(user_id)
    finally:
        if conn:
            conn.close()

def create_default_user(user_id):
    """إنشاء مستخدم جديد"""
    user_data = {
        'user_id': str(user_id),
        'username': "", 
        'first_name': "", 
        'balance': 0.75,
        'referrals_count': 0,
        'referrals_new': 0,
        'games_played_today': 0,
        'total_games_played': 0,
        'total_earned': 0.75,
        'total_deposits': 0.0,
        'vip_level': 0,
        'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_activity': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_reset_date': datetime.now().strftime('%Y-%m-%d'),
        'withdrawal_address': "",
        'registration_days': 0
    }
    save_user(user_data)
    return user_data

def save_user(user_data):
    """حفظ بيانات المستخدم"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    username=EXCLUDED.username, first_name=EXCLUDED.first_name, 
                    balance=EXCLUDED.balance, referrals_count=EXCLUDED.referrals_count,
                    referrals_new=EXCLUDED.referrals_new, games_played_today=EXCLUDED.games_played_today,
                    total_games_played=EXCLUDED.total_games_played, total_earned=EXCLUDED.total_earned,
                    total_deposits=EXCLUDED.total_deposits, vip_level=EXCLUDED.vip_level,
                    last_activity=EXCLUDED.last_activity, last_reset_date=EXCLUDED.last_reset_date,
                    withdrawal_address=EXCLUDED.withdrawal_address, registration_days=EXCLUDED.registration_days
            """, (
                user_data['user_id'], user_data['username'], user_data['first_name'], 
                user_data['balance'], user_data['referrals_count'], user_data['referrals_new'],
                user_data['games_played_today'], user_data['total_games_played'], 
                user_data['total_earned'], user_data['total_deposits'], user_data['vip_level'],
                user_data['registration_date'], user_data['last_activity'], 
                user_data['last_reset_date'], user_data['withdrawal_address'], user_data['registration_days']
            ))
            conn.commit()
            return True
            
    except Exception as e:
        print(f"❌ خطأ في حفظ البيانات: {e}")
        return False
    finally:
        if conn:
            conn.close()

# 🎯 أمر Start بسيط للتجربة
@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        user = get_user(message.from_user.id)
        user['first_name'] = message.from_user.first_name or "مستخدم"
        save_user(user)
        
        bot.reply_to(message, f"🎉 أهلاً {user['first_name']}! رصيدك: {user['balance']} USDT")
        
    except Exception as e:
        bot.reply_to(message, "❌ حدث خطأ")

# 🚀 تشغيل البوت
def run_bot():
    while True:
        try:
            print("🚀 بدء تشغيل البوت...")
            if init_database():
                bot.polling(none_stop=True, timeout=60)
            else:
                print("❌ فشل تهيئة قاعدة البيانات، إعادة المحاولة بعد 10 ثواني...")
                time.sleep(10)
        except Exception as e:
            print(f"❌ خطأ: {e}، إعادة التشغيل بعد 10 ثواني...")
            time.sleep(10)

if __name__ == "__main__":
    print("🎯 بدء نظام البوت...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    print("🌐 بدء خادم Flask...")
    app.run(host='0.0.0.0', port=10000, debug=False)
