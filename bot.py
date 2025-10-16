import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# إعدادات البوت
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7973697789:AAFXfYXTgYaTAF1j7IGhp2kiv-kxrN1uImk')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '8400225549'))
SUPPORT_USERNAME = "@Trust_wallet_Support_4"

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بادئ命令 مع الأزرار"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral")],
        [InlineKeyboardButton("🆘 الدعم الفني", callback_data="support")],
        [InlineKeyboardButton("ℹ️ حول البوت", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
    🎊 أهلاً وسهلاً {user.first_name}!

    **مرحباً بك في البوت الرسمي** 🤖

    ⚡ اختر أحد الخيارات من الأزرار أدناه:
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ضغطات الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    if data == "referral":
        referral_link = f"https://t.me/{context.bot.username}?start=ref{user.id}"
        text = f"""
        🎯 **نظام الاحالات**

        🔗 رابطك الخاص:
        `{referral_link}`

        📊 **مميزات النظام:**
        • احصل على عمولة لكل مستخدم جديد
        • تتبع عدد الاحالات
        • مكافآت تراكمية

        🎁 **المكافآت:**
        - 5 احالات: مكافئة 10$
        - 10 احالات: مكافئة 25$
        - 20 احالات: مكافئة 50$

        📤 شارك الرابط مع أصدقائك وابدأ الربح!
        """
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back")]]
        
    elif data == "support":
        text = f"""
        🆘 **الدعم الفني**

        👨‍💻 **الدعم المباشر:**
        {SUPPORT_USERNAME}

        🕒 **أوقات العمل:**
        • 24/7 على مدار الساعة

        ⚡ **سيتم الرد عليك خلال دقائق**
        """
        keyboard = [
            [InlineKeyboardButton("💬 تواصل مع الدعم", url=f"https://t.me/{SUPPORT_USERNAME[1:]}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
        ]
        
    elif data == "about":
        text = """
        ℹ️ **حول البوت**

        🤖 **البوت الرسمي للعملات**
        
        🎯 **المميزات:**
        • نظام احالات متكامل
        • دعم فني على مدار الساعة
        • واجهة مستخدم سهلة
        • أمان وحماية عالية

        ⚡ **الإصدار:** 2.0
        """
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back")]]
        
    elif data == "back":
        return await start(update, context)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أوامر الإشراف للمشرف فقط"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية للوصول إلى هذه الأوامر!")
        return
    
    text = """
    👑 **أوامر الإشراف**

    📊 /stats - عرض إحصائيات البوت
    📢 /broadcast - بث رسالة لجميع المستخدمين
    ⚙️ /settings - إعدادات البوت
    """
    
    await update.message.reply_text(text)

def main():
    """الدالة الرئيسية"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_commands))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # بدء البوت
    application.run_polling()
    print("✅ البوت يعمل الآن...")

if __name__ == '__main__':
    main()
