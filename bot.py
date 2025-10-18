import os
import telebot
from flask import Flask
import logging
import time

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

# معالجة جميع الرسائل
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_info = f"{message.from_user.first_name} (ID: {message.from_user.id})"
    print(f"📩 رسالة جديدة من {user_info}: {message.text}")
    
    try:
        response = f"مرحباً {message.from_user.first_name}! ✅\n"
        response += f"📱 رسالتك: {message.text}\n"
        response += f"🆔 معرفك: {message.from_user.id}\n"
        response += f"⏰ الوقت: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        bot.send_message(message.chat.id, response)
        print(f"✅ تم الرد على {user_info}")
        
    except Exception as e:
        print(f"❌ فشل في إرسال الرد: {e}")

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
