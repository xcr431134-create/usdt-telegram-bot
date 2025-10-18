import os
import telebot
from flask import Flask

BOT_TOKEN = os.environ.get('BOT_TOKEN', '7973697789:AAFXfYXTgYaTAF1j7IGhp2kiv-kxrN1uImk')
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "البوت شغال! ✅"

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "أهلاً! البوت يشتغل بنجاح 🎉")

def run():
    print("🚀 جاري تشغيل البوت...")
    bot.polling()

if __name__ == "__main__":
    run()
