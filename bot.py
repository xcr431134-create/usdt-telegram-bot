import os
import telebot
import random
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import time
from flask import Flask
import logging
import requests
from pymongo import MongoClient
from bson import ObjectId

# ✅ تفعيل السجلات
logging.basicConfig(level=logging.INFO)
print("🚀 Starting Multi-Language Bot with MongoDB...")

# فحص BOT_TOKEN
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN not found!")
    exit(1)

# 🔗 اتصال MongoDB
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://telegram_bot_user:P8zc2s251FsZFv3X@cluster0.tyuqdos.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')

try:
    client = MongoClient(MONGO_URI)
    db = client['usdt_bot']
    users_collection = db['users']
    print("✅ Connected to MongoDB successfully")
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")
    exit(1)

# تعريف البوت
bot = telebot.TeleBot(BOT_TOKEN)

# 🔐 إعدادات المشرفين
ADMIN_IDS = [8400225549]
YOUR_USER_ID = 8400225549

def is_admin(user_id):
    return user_id in ADMIN_IDS

# مستويات VIP
VIP_LEVELS = {
    0: {"name_ar": "🟢 مبتدئ", "name_en": "🟢 Beginner", "daily_bonus": 0.8, "max_attempts": 3, "price": 0},
    1: {"name_ar": "🟢 برونز", "name_en": "🟢 Bronze", "daily_bonus": 1.25, "max_attempts": 5, "price": 5},
    2: {"name_ar": "🔵 سيلفر", "name_en": "🔵 Silver", "daily_bonus": 1.75, "max_attempts": 8, "price": 10},
    3: {"name_ar": "🟡 جولد", "name_en": "🟡 Gold", "daily_bonus": 2.75, "max_attempts": 13, "price": 20}
}

# نظام اللغات
LANGUAGES = {
    'ar': {
        'main_menu': "✨ **الملف الشخصي المتقدم** ✨",
        'user': "👤 **المستخدم:**",
        'user_id': "🆔 **المعرف:**",
        'membership': "📅 **مدة العضوية:**",
        'balance': "💰 **الرصيد:**",
        'total_earnings': "💎 **إجمالي الأرباح:**",
        'total_deposits': "💳 **إجمالي الإيداعات:**",
        'vip_level': "🏆 **المستوى:**",
        'daily_attempts': "🎯 **محاولات اليوم:**",
        'referrals': "👥 **الإحالات:**",
        'daily_bonus': "⏰ **المكافأة اليومية:**",
        'withdraw_status': "🔐 **حالة السحب:**",
        'registration_date': "📅 **تاريخ التسجيل:**",
        'games_btn': "🎮 ألعاب الربح",
        'vip_btn': "💎 ترقية VIP",
        'referral_btn': "👥 نظام الإحالات",
        'withdraw_btn': "💰 سحب الأرباح",
        'deposit_btn': "💳 إيداع الرصيد",
        'daily_bonus_btn': "🎁 المكافأة اليومية",
        'support_btn': "🆘 الدعم الفني",
        'refresh_btn': "🔄 تحديث البيانات",
        'back_btn': "🔙 رجوع",
        'active': "✅ **مفعل**",
        'inactive': "❌ **غير مفعل**",
        'days_remaining': "متبقي",
        'ready': "جاهز الآن! 🎁"
    },
    'en': {
        'main_menu': "✨ **Advanced Profile** ✨",
        'user': "👤 **User:**",
        'user_id': "🆔 **ID:**",
        'membership': "📅 **Membership:**",
        'balance': "💰 **Balance:**",
        'total_earnings': "💎 **Total Earnings:**",
        'total_deposits': "💳 **Total Deposits:**",
        'vip_level': "🏆 **Level:**",
        'daily_attempts': "🎯 **Daily Attempts:**",
        'referrals': "👥 **Referrals:**",
        'daily_bonus': "⏰ **Daily Bonus:**",
        'withdraw_status': "🔐 **Withdrawal Status:**",
        'registration_date': "📅 **Registration Date:**",
        'games_btn': "🎮 Earn Games",
        'vip_btn': "💎 Upgrade VIP",
        'referral_btn': "👥 Referral System",
        'withdraw_btn': "💰 Withdraw Earnings",
        'deposit_btn': "💳 Deposit Balance",
        'daily_bonus_btn': "🎁 Daily Bonus",
        'support_btn': "🆘 Technical Support",
        'refresh_btn': "🔄 Refresh Data",
        'back_btn': "🔙 Back",
        'active': "✅ **Active**",
        'inactive': "❌ **Inactive**",
        'days_remaining': "days left",
        'ready': "Ready Now! 🎁"
    }
}

def get_user_language(user_id):
    """جلب لغة المستخدم - افتراضي عربي"""
    user = get_user(user_id)
    return user.get('language', 'ar')

def set_user_language(user_id, language):
    """تعيين لغة المستخدم"""
    return update_user(user_id, language=language)

def t(user_id, key):
    """ترجمة النص حسب لغة المستخدم"""
    lang = get_user_language(user_id)
    return LANGUAGES[lang].get(key, key)

def init_database():
    """تهيئة قاعدة البيانات"""
    try:
        users_collection.find_one()
        print("✅ Database ready")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def get_user(user_id):
    """جلب بيانات المستخدم من MongoDB"""
    user_id_str = str(user_id)
    try:
        user_data = users_collection.find_one({"user_id": user_id_str})
        
        if user_data:
            user_data.pop('_id', None)
            return user_data
        else:
            # إنشاء مستخدم جديد
            new_user = {
                'user_id': user_id_str,
                'username': "",
                'first_name': "",
                'balance': 0.75,
                'referral_count': 0,
                'new_referrals': 0,
                'vip_level': 0,
                'attempts': 3,
                'total_earnings': 0.75,
                'total_deposits': 0.0,
                'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_activity': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_mining_date': None,
                'withdrawal_address': "",
                'games_played_today': 0,
                'last_reset_date': datetime.now().strftime('%Y-%m-%d'),
                'has_deposit': 0,
                'language': 'ar'  # اللغة الافتراضية
            }
            users_collection.insert_one(new_user)
            return new_user
            
    except Exception as e:
        print(f"❌ Error getting user: {e}")
        return None

def update_user(user_id, **kwargs):
    """تحديث بيانات المستخدم في MongoDB"""
    try:
        user_id_str = str(user_id)
        users_collection.update_one(
            {"user_id": user_id_str},
            {"$set": kwargs}
        )
        return True
    except Exception as e:
        print(f"❌ Error updating user: {e}")
        return False

# نظام الإحالات
def handle_referral_system(message):
    """معالجة نظام الإحالات عند /start"""
    try:
        user_id = message.from_user.id
        
        command_parts = message.text.split()
        
        if len(command_parts) > 1:
            ref_param = command_parts[1]
            
            if ref_param.startswith('ref'):
                try:
                    referrer_id = int(ref_param[3:])
                    
                    if referrer_id != user_id:
                        referrer = get_user(referrer_id)
                        
                        if referrer:
                            update_user(
                                referrer_id,
                                balance=referrer['balance'] + 1.0,
                                total_earnings=referrer['total_earnings'] + 1.0,
                                referral_count=referrer['referral_count'] + 1,
                                new_referrals=referrer['new_referrals'] + 1
                            )
                            
                            # إرسال إشعار للمحيل
                            try:
                                lang = get_user_language(referrer_id)
                                if lang == 'ar':
                                    message_text = f"🎉 **تمت إحالة جديدة!**\n\n👤 تم تسجيل مستخدم جديد عبر رابطك\n💰 تم إضافة 1 USDT إلى رصيدك\n💵 رصيدك الحالي: {referrer['balance'] + 1:.2f} USDT\n📊 إجمالي إحالاتك: {referrer['referral_count'] + 1}"
                                else:
                                    message_text = f"🎉 **New Referral!**\n\n👤 New user registered via your link\n💰 1 USDT added to your balance\n💵 Your balance: {referrer['balance'] + 1:.2f} USDT\n📊 Total referrals: {referrer['referral_count'] + 1}"
                                
                                bot.send_message(referrer_id, message_text)
                            except:
                                pass
                except ValueError:
                    pass
                    
    except Exception as e:
        print(f"❌ Referral system error: {e}")

def get_remaining_attempts(user):
    base_attempts = VIP_LEVELS[user['vip_level']]['max_attempts']
    extra_attempts = user.get('new_referrals', 0)
    used_attempts = user.get('games_played_today', 0)
    total_attempts = base_attempts + extra_attempts
    remaining = total_attempts - used_attempts
    return max(0, remaining), total_attempts, extra_attempts

def get_membership_days(user_id):
    """حساب مدة العضوية والأيام المتبقية"""
    user = get_user(user_id)
    if not user:
        return 0, 10
    
    try:
        reg_date = datetime.strptime(user['registration_date'].split()[0], '%Y-%m-%d')
        days_registered = (datetime.now() - reg_date).days
        days_remaining = max(0, 10 - days_registered)
        return days_registered, days_remaining
    except:
        return 0, 10

def can_withdraw(user):
    """التحقق من إمكانية السحب"""
    try:
        reg_date = datetime.strptime(user['registration_date'].split()[0], '%Y-%m-%d')
        days_registered = (datetime.now() - reg_date).days
        has_10_days = days_registered >= 10
        
        has_150_balance = user['balance'] >= 150
        has_25_refs = user.get('new_referrals', 0) >= 25
        has_deposit = user.get('has_deposit', 0) == 1
        
        return has_deposit and has_150_balance and has_25_refs and has_10_days
    except:
        return False

def get_mining_time_left(user_id):
    """حساب الوقت المتبقي للمكافأة اليومية"""
    user = get_user(user_id)
    if not user or not user['last_mining_date']:
        return t(user_id, 'ready')
    
    try:
        last_mining = datetime.strptime(user['last_mining_date'], '%Y-%m-%d %H:%M:%S')
        next_mining = last_mining + timedelta(hours=24)
        now = datetime.now()
        
        if now >= next_mining:
            return t(user_id, 'ready')
        
        time_left = next_mining - now
        hours = time_left.seconds // 3600
        minutes = (time_left.seconds % 3600) // 60
        
        if hours == 0 and minutes < 5:
            random_minutes = random.randint(1, 5)
            random_seconds = random.randint(1, 59)
            return f"{random_minutes:02d}:{random_seconds:02d} ⏳"
        
        return f"{hours:02d}:{minutes:02d} ⏳"
    except:
        return t(user_id, 'ready')

def claim_daily_bonus(user_id):
    """المطالبة بالمكافأة اليومية"""
    user = get_user(user_id)
    if not user:
        return False, "❌ User not found"
    
    if user.get('last_mining_date'):
        last_claim = datetime.strptime(user['last_mining_date'], '%Y-%m-%d %H:%M:%S')
        next_claim = last_claim + timedelta(hours=24)
        if datetime.now() < next_claim:
            time_left = next_claim - datetime.now()
            hours = time_left.seconds // 3600
            minutes = (time_left.seconds % 3600) // 60
            if get_user_language(user_id) == 'ar':
                return False, f"⏳ انتظر {hours:02d}:{minutes:02d} للمكافأة التالية"
            else:
                return False, f"⏳ Wait {hours:02d}:{minutes:02d} for next bonus"
    
    vip_info = VIP_LEVELS[user['vip_level']]
    daily_bonus = vip_info['daily_bonus']
    
    new_balance = user['balance'] + daily_bonus
    new_earnings = user['total_earnings'] + daily_bonus
    
    success = update_user(
        user_id,
        balance=new_balance,
        total_earnings=new_earnings,
        last_mining_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    if success:
        if get_user_language(user_id) == 'ar':
            return True, f"🎉 **تم استلام المكافأة اليومية!**\n💰 **المبلغ:** {daily_bonus:.2f} USDT\n💵 **الرصيد الجديد:** {new_balance:.2f} USDT"
        else:
            return True, f"🎉 **Daily Bonus Claimed!**\n💰 **Amount:** {daily_bonus:.2f} USDT\n💵 **New Balance:** {new_balance:.2f} USDT"
    else:
        return False, "❌ Failed to claim bonus"

def send_admin_notification(user, service_type, amount=0):
    """إرسال إشعار للمسؤول"""
    try:
        days_registered, _ = get_membership_days(user['user_id'])
        
        notification_text = f"""🆕 **New User Request**

👤 **User:** {user['first_name'] or 'Unknown'}
🆔 **ID:** {user['user_id']}
📞 **Contact:** [Click here](tg://user?id={user['user_id']})

📋 **Service:** {service_type}
{'💰 **Amount:** ' + str(amount) + ' USDT' if amount > 0 else ''}

📅 **Membership:** {days_registered} days
👥 **Referrals:** {user.get('new_referrals', 0)}/25

💵 **Current Balance:** {user['balance']:.1f} USDT
📅 **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ **Request will be processed within 24 hours**"""
        
        bot.send_message(
            YOUR_USER_ID,
            notification_text,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"❌ Notification error: {e}")

# 🎯 الواجهة الرئيسية بلغتين
def show_main_menu(chat_id, message_id=None, user_id=None):
    """عرض القائمة الرئيسية"""
    try:
        if not user_id:
            return False
            
        user_data = get_user(user_id)
        if not user_data:
            return False
            
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user_data)
        vip_info = VIP_LEVELS[user_data['vip_level']]
        days_registered, days_remaining = get_membership_days(user_id)
        
        can_withdraw_user = can_withdraw(user_data)
        lang = get_user_language(user_id)
        
        if lang == 'ar':
            vip_name = vip_info['name_ar']
            status_text = t(user_id, 'active') if can_withdraw_user else t(user_id, 'inactive')
            days_text = f"({days_remaining} {t(user_id, 'days_remaining')})" if days_registered < 10 else "✅"
        else:
            vip_name = vip_info['name_en']
            status_text = t(user_id, 'active') if can_withdraw_user else t(user_id, 'inactive')
            days_text = f"({days_remaining} {t(user_id, 'days_remaining')})" if days_registered < 10 else "✅"
        
        profile_text = f"""
{t(user_id, 'main_menu')}

{t(user_id, 'user')} {user_data['first_name'] or 'New User'}
{t(user_id, 'user_id')} `{user_id}`
{t(user_id, 'membership')} {days_registered}/10 days {days_text}

💼 **Financial Status:**
├ {t(user_id, 'balance')} `{user_data['balance']:.2f} USDT`
├ {t(user_id, 'total_earnings')} `{user_data['total_earnings']:.2f} USDT`
└ {t(user_id, 'total_deposits')} `{user_data['total_deposits']:.2f} USDT`

🏆 **Level & Privileges:**
├ {vip_name}
├ {t(user_id, 'daily_attempts')} {remaining_attempts}/{total_attempts}
└ {t(user_id, 'referrals')} {user_data['referral_count']} users

{t(user_id, 'daily_bonus')} {get_mining_time_left(user_id)}
{t(user_id, 'withdraw_status')} {status_text}
{t(user_id, 'registration_date')} {user_data['registration_date'].split()[0]}
        """
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        # الصف الأول
        keyboard.add(
            InlineKeyboardButton(t(user_id, 'games_btn'), callback_data="games"),
            InlineKeyboardButton(t(user_id, 'vip_btn'), callback_data="vip_services")
        )
        
        # الصف الثاني
        keyboard.add(
            InlineKeyboardButton(t(user_id, 'referral_btn'), callback_data="referral"),
            InlineKeyboardButton(t(user_id, 'withdraw_btn'), callback_data="withdraw")
        )
        
        # الصف الثالث
        keyboard.add(
            InlineKeyboardButton(t(user_id, 'deposit_btn'), callback_data="deposit"),
            InlineKeyboardButton(t(user_id, 'daily_bonus_btn'), callback_data="daily_bonus")
        )
        
        # الصف الرابع
        keyboard.add(
            InlineKeyboardButton(t(user_id, 'support_btn'), url="https://t.me/Trust_wallet_Support_4"),
            InlineKeyboardButton(t(user_id, 'refresh_btn'), callback_data="refresh_profile")
        )
        
        # زر تغيير اللغة
        if lang == 'ar':
            keyboard.add(InlineKeyboardButton("🌐 Switch to English", callback_data="change_language_en"))
        else:
            keyboard.add(InlineKeyboardButton("🌐 التغيير إلى العربية", callback_data="change_language_ar"))
        
        if message_id:
            bot.edit_message_text(
                profile_text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        else:
            bot.send_message(
                chat_id, 
                profile_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        return True
        
    except Exception as e:
        print(f"❌ Error in main menu: {e}")
        return False

# 🎯 معالجة الأوامر
@bot.message_handler(commands=['start', 'profile'])
def handle_start(message):
    try:
        user_id = message.from_user.id
        handle_referral_system(message)
        
        user_data = get_user(user_id)
        update_user(
            user_id,
            first_name=message.from_user.first_name or "",
            username=message.from_user.username or "",
            last_activity=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        show_main_menu(message.chat.id, user_id=user_id)
        
    except Exception as e:
        print(f"❌ Start error: {e}")

@bot.message_handler(commands=['language', 'لغة'])
def handle_language(message):
    """تغيير اللغة"""
    try:
        user_id = message.from_user.id
        current_lang = get_user_language(user_id)
        
        keyboard = InlineKeyboardMarkup()
        if current_lang == 'ar':
            keyboard.add(InlineKeyboardButton("🇺🇸 English", callback_data="change_language_en"))
            text = "🌐 **اختر اللغة:**"
        else:
            keyboard.add(InlineKeyboardButton("🇸🇦 العربية", callback_data="change_language_ar"))
            text = "🌐 **Choose Language:**"
        
        bot.send_message(message.chat.id, text, reply_markup=keyboard)
        
    except Exception as e:
        print(f"❌ Language error: {e}")

# معالجة تغيير اللغة
@bot.callback_query_handler(func=lambda call: call.data.startswith('change_language_'))
def handle_language_change(call):
    try:
        user_id = call.from_user.id
        new_lang = call.data.replace('change_language_', '')
        
        set_user_language(user_id, new_lang)
        
        if new_lang == 'ar':
            message_text = "✅ **تم تغيير اللغة إلى العربية**"
        else:
            message_text = "✅ **Language changed to English**"
        
        bot.answer_callback_query(call.id, message_text)
        show_main_menu(call.message.chat.id, call.message.message_id, user_id)
        
    except Exception as e:
        print(f"❌ Language change error: {e}")

# باقي ال handlers تبقى كما هي مع إضافة الترجمات
@bot.callback_query_handler(func=lambda call: call.data == "back_to_profile")
def back_to_profile(call):
    try:
        show_main_menu(call.message.chat.id, call.message.message_id, call.from_user.id)
        bot.answer_callback_query(call.id, "✅ Done")
    except Exception as e:
        print(f"❌ Back error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "refresh_profile")
def refresh_profile(call):
    try:
        show_main_menu(call.message.chat.id, call.message.message_id, call.from_user.id)
        bot.answer_callback_query(call.id, "✅ Updated")
    except Exception as e:
        print(f"❌ Refresh error: {e}")

# نظام الألعاب بلغتين
@bot.callback_query_handler(func=lambda call: call.data == "games")
def show_games(call):
    try:
        user = get_user(call.from_user.id)
        remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
        lang = get_user_language(call.from_user.id)
        
        if lang == 'ar':
            games_text = f"""🎮 **قائمة الألعاب**

🎯 **المحاولات المتبقية:** {remaining_attempts}/{total_attempts}
💰 **الربح لكل محاولة:** 2.5 USDT

اختر اللعبة:"""
        else:
            games_text = f"""🎮 **Games List**

🎯 **Remaining Attempts:** {remaining_attempts}/{total_attempts}
💰 **Earnings per attempt:** 2.5 USDT

Choose game:"""
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        if lang == 'ar':
            keyboard.add(
                InlineKeyboardButton("🎰 سلوت", callback_data="game_slot"),
                InlineKeyboardButton("🎲 نرد", callback_data="game_dice")
            )
            keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        else:
            keyboard.add(
                InlineKeyboardButton("🎰 Slots", callback_data="game_slot"),
                InlineKeyboardButton("🎲 Dice", callback_data="game_dice")
            )
            keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="back_to_profile"))
        
        bot.edit_message_text(
            games_text, 
            call.message.chat.id, 
            call.message.message_id, 
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"❌ Games error: {e}")

# باقي الأنظمة (VIP، الإيداع، السحب، الإحالات) بنفس الطريقة...

# 🔧 نظام التشغيل
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot is running! Send /start to begin"

@app.route('/health')
def health():
    return "✅ OK", 200

@app.route('/keepalive')
def keepalive():
    return "🔄 Bot active", 200

def run_bot():
    """تشغيل البوت"""
    print("🔄 Starting bot...")
    
    try:
        bot.remove_webhook()
        time.sleep(3)
    except:
        pass
    
    if not init_database():
        print("⚠️ Continuing without database")
    
    while True:
        try:
            print("🚀 Bot is running...")
            bot.infinity_polling()
        except Exception as e:
            print(f"❌ Bot error: {e}")
            time.sleep(20)

def run_flask_server():
    """تشغيل Flask"""
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("🎯 Multi-Language Bot - Ready!")
    
    import threading
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    time.sleep(5)
    run_bot()
