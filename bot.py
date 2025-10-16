import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    exit(1)

print(f"✅ Token loaded: {BOT_TOKEN[:10]}...")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    print(f"🚀 User {user.id} started the bot")
    
    keyboard = [
        [InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral")],
        [InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"أهلاً {user.first_name}! 👋\nاختر من الأزرار:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "referral":
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start=ref{query.from_user.id}"
        await query.edit_message_text(f"🎯 رابطك الخاص:\n`{referral_link}`")

def main():
    try:
        print("🔄 Starting bot...")
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        print("✅ Bot is running...")
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == '__main__':
    main()
