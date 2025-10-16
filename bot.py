import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# التوكن - تأكد من البيئة
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found in environment variables!")
    exit(1)

print(f"✅ Token loaded: {BOT_TOKEN[:10]}...")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    print(f"🚀 User {user.id} started the bot")
    
    keyboard = [
        [InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral")],
        [InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"أهلاً {user.first_name}! 👋\nاختر من الأزرار:",
        reply_markup=reply_markup
    )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.data == "referral":
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start=ref{query.from_user.id}"
        query.edit_message_text(f"🎯 رابطك الخاص:\n`{referral_link}`")

def main():
    try:
        print("🔄 Starting bot...")
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher
        
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CallbackQueryHandler(button_handler))
        
        print("✅ Bot is running...")
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == '__main__':
    main()
