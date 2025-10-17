import os
import telebot
import json
import random
import threading
import gspread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import shutil
import time
import requests
from google.oauth2.service_account import Credentials
from flask import Flask

# 📡 Flask Server for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 USDT Telegram Bot is Running!"

@app.route('/health')
def health_check():
    return "✅ OK", 200

# 🔧 الإعدادات من environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN', '7973697789:AAFXfYXTgYaTAF1j7IGhp2kiv-kxrN1uImk')
ADMIN_IDS = [int(os.getenv('ADMIN_ID', '8400225549'))]
DATA_FILE = "users_data.json"

bot = telebot.TeleBot(BOT_TOKEN)

# 📊 Google Sheets Integration
def init_google_sheets():
    """تهيئة الاتصال بـ Google Sheets"""
    try:
        # استخدام environment variable بدلاً من ملف
        creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        if creds_json:
            creds_dict = json.loads(creds_json)
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            client = gspread.authorize(creds)
            return client.open("Bot-Users").sheet1
        else:
            print("⚠️ GOOGLE_SHEETS_CREDENTIALS not found in environment variables")
    except Exception as e:
        print(f"❌ خطأ في تهيئة Google Sheets: {e}")
    return None

def sync_user_to_sheets(user_data):
    """مزامنة بيانات المستخدم مع Google Sheets"""
    try:
        sheet = init_google_sheets()
        if not sheet:
            return False
            
        # البحث عن المستخدم في الورقة
        users = sheet.get_all_records()
        user_id = user_data['user_id']
        
        # تحضير البيانات
        row_data = [
            user_data['user_id'],
            user_data.get('first_name', ''),
            user_data.get('balance', 0),
            user_data.get('referrals_count', 0),
            user_data.get('referrals_new', 0),
            user_data.get('games_played_today', 0),
            user_data.get('total_games_played', 0),
            user_data.get('total_earned', 0),
            user_data.get('total_deposits', 0),
            user_data.get('vip_level', 0),
            user_data.get('registration_date', ''),
            user_data.get('last_activity', ''),
            user_data.get('withdrawal_address', ''),
            user_data.get('registration_days', 0)
        ]
        
        # البحث عن الصف الموجود أو إضافة جديد
        found = False
        for i, user in enumerate(users, start=2):  # start=2 لأن الصف الأول للعناوين
            if str(user['user_id']) == str(user_id):
                sheet.update(f'A{i}:N{i}', [row_data])
                found = True
                break
        
        if not found:
            sheet.append_row(row_data)
            
        print(f"✅ تم مزامنة user_id {user_id} مع Google Sheets")
        return True
    except Exception as e:
        print(f"❌ خطأ في المزامنة مع Google Sheets: {e}")
        return False

def load_users():
    """تحميل البيانات من الملف"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"📂 تم تحميل {len(data)} مستخدم من الذاكرة")
            return data
    except FileNotFoundError:
        print("📂 لا يوجد بيانات سابقة، سيتم إنشاء ملف جديد")
        return {}
    except Exception as e:
        print(f"❌ خطأ في تحميل البيانات: {e}")
        return {}

def save_users(users_data):
    """حفظ البيانات في الملف ومزامنة مع Google Sheets"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        print(f"💾 تم حفظ {len(users_data)} مستخدم في الذاكرة")
        
        # مزامنة جميع المستخدمين مع Google Sheets
        for user_data in users_data.values():
            sync_user_to_sheets(user_data)
            
        return True
    except Exception as e:
        print(f"❌ خطأ في حفظ البيانات: {e}")
        return False

def get_user(user_id):
    """جلب بيانات المستخدم"""
    users_data = load_users()
    user_id_str = str(user_id)
    
    if user_id_str in users_data:
        user_data = users_data[user_id_str]
        
        # تحديث المحاولات إذا انتهى اليوم
        last_reset = user_data.get('last_reset_date', '2000-01-01')
        today = datetime.now().strftime('%Y-%m-%d')
        
        if last_reset != today:
            user_data['games_played_today'] = 0
            user_data['last_reset_date'] = today
            
            # منح المكافأة اليومية
            daily_bonus = 0.75
            user_data['balance'] += daily_bonus
            user_data['total_earned'] += daily_bonus
            print(f"🎁 منح مكافأة يومية {daily_bonus} لـ {user_id}")
            
            # منح مكافآت VIP
            vip_bonus = {
                1: 0.5,  # برونز
                2: 1.0,  # سيلفر
                3: 2.0   # جولد
            }
            if user_data['vip_level'] in vip_bonus:
                bonus = vip_bonus[user_data['vip_level']]
                user_data['balance'] += bonus
                user_data['total_earned'] += bonus
                print(f"💎 منح مكافأة VIP {bonus} لـ {user_id}")
            
            save_users(users_data)
        
        return user_data
    
    # إنشاء مستخدم جديد
    user_data = {
        'user_id': user_id_str,
        'username': "",
        'first_name': "",
        'balance': 0.75,  # مكافأة ترحيبية
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
        'registration_days': 0,
        'last_daily_check': datetime.now().strftime('%Y-%m-%d')
    }
    
    users_data[user_id_str] = user_data
    save_users(users_data)
    print(f"🆕 تم إنشاء مستخدم جديد: {user_id_str}")
    return user_data

def save_user(user_data):
    """حفظ بيانات مستخدم"""
    users_data = load_users()
    user_id = user_data['user_id']
    users_data[user_id] = user_data
    
    print(f"💾 حفظ بيانات user_id: {user_id}, الرصيد: {user_data['balance']}")
    
    # مزامنة مع Google Sheets
    sync_user_to_sheets(user_data)
    
    return save_users(users_data)

def update_user_activity(user_id):
    user = get_user(user_id)
    user['last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # تحديث أيام التسجيل
    registration_date = datetime.strptime(user['registration_date'].split()[0], '%Y-%m-%d')
    current_date = datetime.now()
    days_registered = (current_date - registration_date).days
    user['registration_days'] = days_registered
    
    save_user(user)

def get_vip_level_name(level):
    """تحويل مستوى VIP إلى اسم"""
    vip_names = {
        0: "🟢 مبتدئ",
        1: "🟢 برونز", 
        2: "🔵 سيلفر",
        3: "🟡 جولد"
    }
    return vip_names.get(level, "🟢 مبتدئ")

def get_remaining_attempts(user):
    """حساب المحاولات المتبقية"""
    base_attempts = 3
    extra_attempts = user.get('referrals_new', 0)
    used_attempts = user.get('games_played_today', 0)
    total_attempts = base_attempts + extra_attempts
    remaining = total_attempts - used_attempts
    return max(0, remaining), total_attempts, extra_attempts

def get_mining_reward_time():
    """وقت مكافأة التعدين (حقيقي وليس عشوائي)"""
    now = datetime.now()
    next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    time_left = next_reset - now
    
    hours = int(time_left.total_seconds() // 3600)
    minutes = int((time_left.total_seconds() % 3600) // 60)
    
    return f"{hours:02d}س {minutes:02d}د ⏳"

def can_withdraw(user):
    """التحقق من إمكانية السحب"""
    has_10_days = user.get('registration_days', 0) >= 10
    has_150_balance = user['balance'] >= 150
    has_address = bool(user.get('withdrawal_address', ''))
    return has_10_days and has_150_balance and has_address

# 🎯 الواجهة الرئيسية
@bot.message_handler(commands=['start', 'profile'])
def start_command(message):
    try:
        user = get_user(message.from_user.id)
        # ✅ الإصلاح: حفظ اسم المستخدم الحقيقي من تيليجرام
        user['first_name'] = message.from_user.first_name or "مستخدم"
        user['username'] = message.from_user.username or ""
        update_user_activity(message.from_user.id)
        
        # حساب المحاولات المتبقية
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
        vip_name = get_vip_level_name(user['vip_level'])
        mining_time = get_mining_reward_time()
        
        # ✅ الإصلاح: استخدام الاسم الحقيقي من تيليجرام مباشرة
        user_name = message.from_user.first_name or "مستخدم"
        
        # النص الرئيسي
        profile_text = f"""📊 الملف الشخصي

👤 المستخدم: {user_name}
🆔 المعرف: {message.from_user.id}
💰 الرصيد: {user['balance']:.1f} USDT
👥 الإحالات: {user['referrals_count']} مستخدم
📈 الإحالات الجديدة: {user.get('referrals_new', 0)}/{user['referrals_count']}
🏆 مستوى VIP: {vip_name}
🎯 المحاولات المتبقية: {remaining_attempts} ({total_attempts} أساسية + {extra_attempts} إضافية)
📅 أيام التسجيل: {user.get('registration_days', 0)} يوم

⏰ مكافأة التعدين: {mining_time}

💎 إجمالي الأرباح: {user['total_earned']:.1f} USDT
💳 إجمالي الإيداعات: {user['total_deposits']:.1f} USDT
📅 تاريخ التسجيل: {user['registration_date'].split()[0]}"""

        # الأزرار
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎮 الألعاب", callback_data="games"),
            InlineKeyboardButton("💎 خدمات VIP", callback_data="vip_services"),
            InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral"),
            InlineKeyboardButton("💰 السحب", callback_data="withdraw")
        )
        keyboard.add(
            InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4")
        )
        
        bot.send_message(message.chat.id, profile_text, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ خطأ في start_command: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")

# 🎮 قائمة الألعاب
@bot.callback_query_handler(func=lambda call: call.data == "games")
def show_games(call):
    try:
        user = get_user(call.from_user.id)
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
        
        games_text = f"""🎮 قائمة الألعاب

المحاولات المتبقية: {remaining_attempts}/{total_attempts}
🎰 الربح لكل محاولة: 2.5 USDT

اختر اللعبة:"""
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎰 سلوت", callback_data="game_slot"),
            InlineKeyboardButton("🎲 نرد", callback_data="game_dice")
        )
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        
        bot.edit_message_text(games_text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ خطأ في show_games: {e}")

# 🎰 لعبة السلوت
@bot.callback_query_handler(func=lambda call: call.data == "game_slot")
def play_slot(call):
    try:
        user = get_user(call.from_user.id)
        remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
        
        if remaining_attempts <= 0:
            bot.answer_callback_query(call.id, "❌ لا توجد محاولات متبقية اليوم!", show_alert=True)
            return
        
        user['games_played_today'] += 1
        user['total_games_played'] += 1
        
        symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎"]
        result = [random.choice(symbols) for _ in range(3)]
        
        if result[0] == result[1] == result[2]:
            win_amount = 2.5
            win_text = "🎉 ربح كبير!"
        elif result[0] == result[1] or result[1] == result[2]:
            win_amount = 1.25
            win_text = "👍 ربح جيد!"
        else:
            win_amount = 0
            win_text = "😞 حاول مرة أخرى"
        
        user['balance'] += win_amount
        if win_amount > 0:
            user['total_earned'] += win_amount
        
        save_user(user)
        remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
        
        game_result = f"""🎰 لعبة السلوت

{' | '.join(result)}

{win_text}
💰 الربح: {win_amount:.2f} USDT

🎯 المحاولات المتبقية: {remaining_attempts}/{total_attempts}"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🎰 العب مرة أخرى", callback_data="game_slot"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع للألعاب", callback_data="games"))
        
        bot.edit_message_text(game_result, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ خطأ في play_slot: {e}")

# 🎲 لعبة النرد
@bot.callback_query_handler(func=lambda call: call.data == "game_dice")
def play_dice(call):
    try:
        user = get_user(call.from_user.id)
        remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
        
        if remaining_attempts <= 0:
            bot.answer_callback_query(call.id, "❌ لا توجد محاولات متبقية اليوم!", show_alert=True)
            return
        
        user['games_played_today'] += 1
        user['total_games_played'] += 1
        
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        if total == 7:
            win_amount = 2.5
            win_text = "🎉 ربح كبير! (رقم الحظ)"
        elif total >= 10:
            win_amount = 1.5
            win_text = "👍 ربح جيد!"
        elif total <= 4:
            win_amount = 1.0
            win_text = "👌 ربح صغير"
        else:
            win_amount = 0
            win_text = "😞 حاول مرة أخرى"
        
        user['balance'] += win_amount
        if win_amount > 0:
            user['total_earned'] += win_amount
        
        save_user(user)
        remaining_attempts, total_attempts, _ = get_remaining_attempts(user)
        
        game_result = f"""🎲 لعبة النرد

🎲 النرد: {dice1} + {dice2} = {total}

{win_text}
💰 الربح: {win_amount:.2f} USDT

🎯 المحاولات المتبقية: {remaining_attempts}/{total_attempts}"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🎲 العب مرة أخرى", callback_data="game_dice"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع للألعاب", callback_data="games"))
        
        bot.edit_message_text(game_result, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ خطأ في play_dice: {e}")

# 💎 خدمات VIP - مع الأسعار المحددة
@bot.callback_query_handler(func=lambda call: call.data == "vip_services")
def show_vip_services(call):
    try:
        vip_text = """💎 العضويات VIP المميزة:

🟢 برونز VIP - 5 USDT:
• +10% تعدين
• مكافأة يومية 0.5 USDT
• +2 محاولات ألعاب يومية

🔵 سيلفر VIP - 10 USDT:
• +25% تعدين  
• مكافأة يومية 1.0 USDT
• +5 محاولات ألعاب يومية

🟡 جولد VIP - 20 USDT:
• +50% تعدين
• مكافأة يومية 2.0 USDT
• +10 محاولات ألعاب يومية

اختر العضوية المناسبة:"""
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("🟢 شراء برونز VIP - 5 USDT", callback_data="buy_bronze"),
            InlineKeyboardButton("🔵 شراء سيلفر VIP - 10 USDT", callback_data="buy_silver"),
            InlineKeyboardButton("🟡 شراء جولد VIP - 20 USDT", callback_data="buy_gold"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile")
        )
        
        bot.edit_message_text(vip_text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    except Exception as e:
        print(f"❌ خطأ في show_vip_services: {e}")

# إرسال طلبات الشراء للادمن
@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_vip_purchase(call):
    try:
        user = get_user(call.from_user.id)
        vip_type = call.data.replace('buy_', '')
        
        vip_names = {
            'bronze': '🟢 برونز VIP',
            'silver': '🔵 سيلفر VIP', 
            'gold': '🟡 جولد VIP'
        }
        
        vip_prices = {
            'bronze': 5.0,
            'silver': 10.0,
            'gold': 20.0
        }
        
        vip_name = vip_names.get(vip_type, 'VIP')
        vip_price = vip_prices.get(vip_type, 0)
        
        request_text = f"""🛒 طلب شراء جديد:

👤 المستخدم: {user['first_name']} 
🆔 الآيدي: {call.from_user.id}
📞 للتواصل: [اضغط هنا](tg://user?id={call.from_user.id})
💎 النوع: {vip_name}
💰 السعر: {vip_price} USDT
💰 الرصيد الحالي: {user['balance']:.1f} USDT
📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⏰ الرجاء التواصل مع المستخدم مباشرة بالضغط على الرابط أعلاه"""
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, request_text, parse_mode='Markdown')
            except Exception as e:
                print(f"❌ Failed to send to admin {admin_id}: {e}")
        
        bot.answer_callback_query(
            call.id, 
            f"✅ تم إرسال طلب شراء {vip_name} بقيمة {vip_price} USDT للإدارة\nسيتم التواصل معك قريباً", 
            show_alert=True
        )
    except Exception as e:
        print(f"❌ خطأ في handle_vip_purchase: {e}")

# 💰 نظام السحب
@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def handle_withdraw(call):
    try:
        user = get_user(call.from_user.id)
        
        if not can_withdraw(user):
            if user.get('registration_days', 0) < 10:
                error_msg = f"❌ تحتاج إلى 10 أيام تسجيل على الأقل للسحب\n📅 أيامك الحالية: {user.get('registration_days', 0)} يوم"
            elif user['balance'] < 150:
                error_msg = f"❌ الحد الأدنى للسحب هو 150 USDT\n💰 رصيدك الحالي: {user['balance']:.1f} USDT"
            elif not user.get('withdrawal_address'):
                error_msg = "❌ يرجى إعداد عنوان المحفظة أولاً"
            else:
                error_msg = "❌ لا يمكن السحب حالياً، يرجى المحاولة لاحقاً"
            
            bot.answer_callback_query(call.id, error_msg, show_alert=True)
            return
        
        show_withdrawal_options(call.message, user)
    except Exception as e:
        print(f"❌ خطأ في handle_withdraw: {e}")

def show_withdrawal_options(message, user):
    try:
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("💰 سحب 150 USDT", callback_data="withdraw_150"),
            InlineKeyboardButton("💰 سحب 300 USDT", callback_data="withdraw_300"),
            InlineKeyboardButton("💰 سحب 500 USDT", callback_data="withdraw_500"),
            InlineKeyboardButton("💰 سحب كل الرصيد", callback_data="withdraw_all")
        )
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        
        if not user.get('withdrawal_address'):
            msg = bot.send_message(
                message.chat.id,
                "💰 نظام السحب\n\n"
                "📝 الرجاء إرسال عنوان محفظتك USDT (TRC20):"
            )
            bot.register_next_step_handler(msg, process_withdrawal_address, user)
            return
        
        bot.send_message(
            message.chat.id,
            f"💰 نظام السحب\n\n"
            f"💳 عنوان المحفظة: {user['withdrawal_address']}\n"
            f"💰 الرصيد المتاح: {user['balance']:.1f} USDT\n"
            f"📅 أيام التسجيل: {user.get('registration_days', 0)}/10 يوم\n\n"
            f"اختر مبلغ السحب:",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ خطأ في show_withdrawal_options: {e}")

def process_withdrawal_address(message, user):
    try:
        address = message.text.strip()
        if len(address) < 10:
            msg = bot.send_message(
                message.chat.id,
                "❌ عنوان غير صحيح! الرجاء إرسال عنوان محفظة USDT (TRC20) صحيح:"
            )
            bot.register_next_step_handler(msg, process_withdrawal_address, user)
            return
        
        user['withdrawal_address'] = address
        save_user(user)
        show_withdrawal_options(message, user)
    except Exception as e:
        print(f"❌ خطأ في process_withdrawal_address: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_'))
def process_withdrawal(call):
    try:
        user = get_user(call.from_user.id)
        withdraw_type = call.data.replace('withdraw_', '')
        
        if withdraw_type == '150':
            amount = 150.0
        elif withdraw_type == '300':
            amount = 300.0
        elif withdraw_type == '500':
            amount = 500.0
        else:
            amount = user['balance']
        
        if user['balance'] < amount:
            bot.answer_callback_query(call.id, f"❌ رصيدك غير كافي! الرصيد: {user['balance']:.1f} USDT", show_alert=True)
            return
        
        if amount < 150:
            bot.answer_callback_query(call.id, "❌ الحد الأدنى للسحب هو 150 USDT", show_alert=True)
            return
        
        if user.get('registration_days', 0) < 10:
            bot.answer_callback_query(call.id, f"❌ تحتاج إلى 10 أيام تسجيل للسحب\n📅 أيامك: {user.get('registration_days', 0)}", show_alert=True)
            return
        
        user['balance'] -= amount
        save_user(user)
        
        withdraw_text = f"""🏦 طلب سحب جديد:

👤 المستخدم: {user['first_name']} 
🆔 الآيدي: {call.from_user.id}
📞 للتواصل: [اضغط هنا](tg://user?id={call.from_user.id})
💳 عنوان المحفظة: {user['withdrawal_address']}
💰 المبلغ: {amount:.1f} USDT
📊 الرصيد المتبقي: {user['balance']:.1f} USDT
📅 أيام التسجيل: {user.get('registration_days', 0)} يوم
📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ تم خصم المبلغ من رصيد المستخدم"""
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, withdraw_text, parse_mode='Markdown')
            except Exception as e:
                print(f"❌ Failed to send to admin {admin_id}: {e}")
        
        bot.answer_callback_query(
            call.id, 
            f"✅ تم إرسال طلب سحب {amount:.1f} USDT للإدارة\nسيتم المعالجة خلال 24 ساعة", 
            show_alert=True
        )
    except Exception as e:
        print(f"❌ خطأ في process_withdrawal: {e}")

# 🎯 رابط الاحالات
@bot.callback_query_handler(func=lambda call: call.data == "referral")
def handle_referral(call):
    try:
        update_user_activity(call.from_user.id)
        referral_link = f"https://t.me/{bot.get_me().username}?start=ref{call.from_user.id}"
        
        referral_text = f"""🎯 نظام الإحالات

🔗 رابط الدعوة الخاص بك:
`{referral_link}`

👥 مزايا الإحالات:
• 🎁 1 USDT مكافأة فورية لكل إحالة
• +1 محاولة ألعاب يومية لكل إحالة  
• فرصة ربح مضاعفة
• وصول أسرع لشروط السحب

📤 شارك الرابط مع أصدقائك واكسب المزيد!"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={referral_link}&text=انضم%20إلي%20في%20هذا%20البوت%20الرائع%20واربح%20USDT%20مجاناً!"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_profile"))
        
        bot.edit_message_text(
            referral_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"❌ خطأ في handle_referral: {e}")

# 🔙 رجوع للبروفايل - الإصلاح الكامل
@bot.callback_query_handler(func=lambda call: call.data == "back_to_profile")
def back_to_profile(call):
    try:
        user = get_user(call.from_user.id)
        update_user_activity(call.from_user.id)
        
        # ✅ الإصلاح: استخدام الاسم الحقيقي من تيليجرام مباشرة
        user_name = call.from_user.first_name or "مستخدم"
        
        # حساب المحاولات المتبقية
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
        vip_name = get_vip_level_name(user['vip_level'])
        mining_time = get_mining_reward_time()
        
        # النص الرئيسي المعدل
        profile_text = f"""📊 الملف الشخصي

👤 المستخدم: {user_name}
🆔 المعرف: {call.from_user.id}
💰 الرصيد: {user['balance']:.1f} USDT
👥 الإحالات: {user['referrals_count']} مستخدم
📈 الإحالات الجديدة: {user.get('referrals_new', 0)}/{user['referrals_count']}
🏆 مستوى VIP: {vip_name}
🎯 المحاولات المتبقية: {remaining_attempts} ({total_attempts} أساسية + {extra_attempts} إضافية)
📅 أيام التسجيل: {user.get('registration_days', 0)} يوم

⏰ مكافأة التعدين: {mining_time}

💎 إجمالي الأرباح: {user['total_earned']:.1f} USDT
💳 إجمالي الإيداعات: {user['total_deposits']:.1f} USDT
📅 تاريخ التسجيل: {user['registration_date'].split()[0]}"""

        # الأزرار
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎮 الألعاب", callback_data="games"),
            InlineKeyboardButton("💎 خدمات VIP", callback_data="vip_services"),
            InlineKeyboardButton("🎯 رابط الاحالات", callback_data="referral"),
            InlineKeyboardButton("💰 السحب", callback_data="withdraw")
        )
        keyboard.add(
            InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_4")
        )
        
        # تعديل الرسالة الحالية
        bot.edit_message_text(
            profile_text, 
            call.message.chat.id, 
            call.message.message_id, 
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ خطأ في back_to_profile: {e}")

# معالجة الإحالات من رابط الدعوة
@bot.message_handler(func=lambda message: message.text and message.text.startswith('/start ref'))
def handle_referral_start(message):
    try:
        referrer_id = message.text.split('ref')[-1]
        
        new_user = get_user(message.from_user.id)
        new_user['first_name'] = message.from_user.first_name or "مستخدم"
        new_user['username'] = message.from_user.username or ""
        
        if referrer_id.isdigit():
            referrer = get_user(int(referrer_id))
            if referrer['user_id'] != new_user['user_id']:
                referral_bonus = 1.0
                referrer['balance'] += referral_bonus
                referrer['total_earned'] += referral_bonus
                referrer['referrals_count'] += 1
                referrer['referrals_new'] += 1
                
                save_user(referrer)
                
                try:
                    bot.send_message(
                        int(referrer_id),
                        f"🎉 تهانينا! لقد قام {new_user['first_name']} بالتسجيل من خلال رابطك!\n"
                        f"🎁 تم إضافة 1 USDT إلى رصيدك!\n"
                        f"💰 رصيدك الجديد: {referrer['balance']:.1f} USDT"
                    )
                except:
                    pass
        
        start_command(message)
    except Exception as e:
        print(f"❌ خطأ في handle_referral_start: {e}")

# =============================================
# ⚡ الأوامر الإدارية
# =============================================

@bot.message_handler(commands=['myid'])
def myid(message):
    try:
        update_user_activity(message.from_user.id)
        bot.reply_to(message, f"🆔 معرفك: `{message.from_user.id}`", parse_mode='Markdown')
    except Exception as e:
        print(f"❌ خطأ في myid: {e}")

@bot.message_handler(commands=['quickadd'])
def quick_add(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        update_user_activity(message.from_user.id)
        
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /quickadd [user_id] [amount]")
            return
        
        user_id = int(parts[1])
        amount = float(parts[2])
        
        user = get_user(user_id)
        user['balance'] += amount
        user['total_earned'] += amount
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم إضافة {amount} USDT للمستخدم {user_id}\n💰 الرصيد الجديد: {user['balance']:.1f} USDT")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['addreferral'])
def add_referral(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        update_user_activity(message.from_user.id)
        
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ استخدم: /addreferral [user_id]")
            return
        
        user_id = int(parts[1])
        
        user = get_user(user_id)
        user['referrals_count'] += 1
        user['referrals_new'] += 1
        user['balance'] += 1.0
        user['total_earned'] += 1.0
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم إضافة إحالة للمستخدم {user_id}\n🎁 مكافأة: 1 USDT\n👥 الإحالات الجديدة: {user['referrals_new']}\n👥 الإجمالي: {user['referrals_count']}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setvip'])
def set_vip(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        update_user_activity(message.from_user.id)
        
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /setvip [user_id] [level]\n\n0: مبتدئ\n1: برونز\n2: سيلفر\n3: جولد")
            return
        
        user_id = int(parts[1])
        vip_level = int(parts[2])
        
        if vip_level not in [0, 1, 2, 3]:
            bot.reply_to(message, "❌ مستوى VIP غير صحيح!\n\n0: مبتدئ\n1: برونز\n2: سيلفر\n3: جولد")
            return
        
        user = get_user(user_id)
        old_vip = get_vip_level_name(user['vip_level'])
        user['vip_level'] = vip_level
        new_vip = get_vip_level_name(user['vip_level'])
        
        save_user(user)
        
        bot.reply_to(message, f"✅ تم تعيين مستوى VIP للمستخدم {user_id}\n💎 السابق: {old_vip}\n💎 الجديد: {new_vip}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['userinfo'])
def user_info(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        update_user_activity(message.from_user.id)
        
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ استخدم: /userinfo [user_id]")
            return
        
        user_id = int(parts[1])
        user = get_user(user_id)
        
        remaining_attempts, total_attempts, extra_attempts = get_remaining_attempts(user)
        last_active = user.get('last_activity', 'غير معروف')
        
        info_text = f"""
📊 معلومات المستخدم:

🆔 الآيدي: {user['user_id']}
👤 الاسم: {user['first_name']}
💰 الرصيد: {user['balance']:.1f} USDT
👥 الإحالات: {user['referrals_count']}
🎯 المحاولات: {user['games_played_today']}/{total_attempts} (متبقي: {remaining_attempts})
💎 VIP: {get_vip_level_name(user['vip_level'])}
🎮 الألعاب: {user['total_games_played']}
💳 الإيداعات: {user['total_deposits']:.1f} USDT
🏆 الأرباح: {user['total_earned']:.1f} USDT
📅 مسجل منذ: {user['registration_date']}
📅 أيام التسجيل: {user.get('registration_days', 0)} يوم
🕒 آخر نشاط: {last_active}"""
        
        bot.reply_to(message, info_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        update_user_activity(message.from_user.id)
        
        users_data = load_users()
        users = list(users_data.values())
        
        total_balance = sum(user['balance'] for user in users)
        total_referrals = sum(user['referrals_count'] for user in users)
        total_deposits = sum(user['total_deposits'] for user in users)
        active_users = sum(1 for user in users if user['balance'] > 0 or user['games_played_today'] > 0)
        
        vip_counts = {0: 0, 1: 0, 2: 0, 3: 0}
        for user in users:
            vip_level = user.get('vip_level', 0)
            vip_counts[vip_level] = vip_counts.get(vip_level, 0) + 1
        
        stats_text = f"""
📈 إحصائيات البوت:

👥 إجمالي المستخدمين: {len(users)}
👤 المستخدمين النشطين: {active_users}
💰 إجمالي الرصيد: {total_balance:.1f} USDT
👥 إجمالي الإحالات: {total_referrals}
💳 إجمالي الإيداعات: {total_deposits:.1f} USDT
🎯 مستخدمين بلعبوا اليوم: {sum(1 for user in users if user['games_played_today'] > 0)}

💎 إحصائيات VIP:
🟢 مبتدئ: {vip_counts[0]}
🟢 برونز: {vip_counts[1]}  
🔵 سيلفر: {vip_counts[2]}
🟡 جولد: {vip_counts[3]}"""
        
        bot.reply_to(message, stats_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# =============================================
# 🆕 نظام النسخ الاحتياطي والاستعادة
# =============================================

@bot.message_handler(commands=['backup'])
def backup_data(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_users_data_{timestamp}.json"
        
        shutil.copy2(DATA_FILE, backup_file)
        
        with open(backup_file, 'rb') as f:
            bot.send_document(
                message.chat.id, 
                f,
                caption=f"📦 النسخة الاحتياطية - {timestamp}\n"
                       f"💾 الملف: {DATA_FILE}\n"
                       f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        bot.reply_to(message, f"✅ تم إنشاء نسخة احتياطية: {backup_file}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في النسخ الاحتياطي: {e}")

@bot.message_handler(commands=['restore'])
def restore_data(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        msg = bot.reply_to(message, "📤 الرجاء إرسال ملف النسخة الاحتياطية (JSON):")
        bot.register_next_step_handler(msg, process_restore_file)
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في الاستعادة: {e}")

def process_restore_file(message):
    try:
        if not message.document:
            bot.reply_to(message, "❌ لم يتم إرسال ملف!")
            return
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        temp_file = "temp_restore.json"
        with open(temp_file, 'wb') as f:
            f.write(downloaded_file)
        
        with open(temp_file, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        if not isinstance(test_data, dict):
            bot.reply_to(message, "❌ الملف غير صالح!")
            return
        
        backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(DATA_FILE, f"pre_restore_backup_{backup_timestamp}.json")
        
        shutil.copy2(temp_file, DATA_FILE)
        
        os.remove(temp_file)
        
        bot.reply_to(
            message, 
            f"✅ تم استعادة البيانات بنجاح!\n"
            f"📊 عدد المستخدمين: {len(test_data)}\n"
            f"💾 تم إنشاء نسخة احتياطية قبل الاستعادة: pre_restore_backup_{backup_timestamp}.json"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في استعادة الملف: {e}")

@bot.message_handler(commands=['copydata'])
def copy_user_data(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ استخدم: /copydata [from_user_id] [to_user_id]")
            return
        
        from_user_id = int(parts[1])
        to_user_id = int(parts[2])
        
        users_data = load_users()
        
        if str(from_user_id) not in users_data:
            bot.reply_to(message, f"❌ المستخدم المصدر {from_user_id} غير موجود!")
            return
        
        from_user_data = users_data[str(from_user_id)]
        to_user_data = get_user(to_user_id)
        
        fields_to_copy = [
            'balance', 'referrals_count', 'referrals_new', 'total_earned',
            'total_deposits', 'vip_level', 'games_played_today', 'total_games_played'
        ]
        
        copied_fields = []
        for field in fields_to_copy:
            if field in from_user_data:
                old_value = to_user_data.get(field, 0)
                to_user_data[field] = from_user_data[field]
                copied_fields.append(f"{field}: {old_value} → {from_user_data[field]}")
        
        save_user(to_user_data)
        
        bot.reply_to(
            message,
            f"✅ تم نسخ البيانات من {from_user_id} إلى {to_user_id}\n\n"
            f"📊 الحقول المنسوخة:\n" + "\n".join(copied_fields)
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في نسخ البيانات: {e}")

@bot.message_handler(commands=['fileinfo'])
def file_info(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ ليس لديك صلاحية!")
        return
    
    try:
        file_path = os.path.abspath(DATA_FILE)
        file_size = os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0
        file_exists = os.path.exists(DATA_FILE)
        
        users_data = load_users()
        
        info_text = f"""
📁 معلومات ملف البيانات:

📍 المسار: `{file_path}`
📦 الحجم: {file_size} بايت
✅ موجود: {'نعم' if file_exists else 'لا'}
👥 عدد المستخدمين: {len(users_data)}
💾 آخر تعديل: {time.ctime(os.path.getmtime(DATA_FILE)) if file_exists else 'غير متوفر'}

💡 لتحميل نسخة احتياطية: /backup
💡 لاستعادة بيانات: /restore"""
        
        bot.reply_to(message, info_text, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

# =============================================
# 💓 نظام النبضات المحسن
# =============================================

def heartbeat_loop():
    """إرسال نبضات دورية"""
    while True:
        try:
            urls = [
                "https://www.google.com",
                "https://www.cloudflare.com"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        print(f"💓 نبضة ناجحة إلى {url} - {datetime.now().strftime('%H:%M:%S')}")
                except:
                    print(f"⚠️ فشل النبضة إلى {url}")
            
            time.sleep(300)
            
        except Exception as e:
            print(f"❌ خطأ في النبضات: {e}")
            time.sleep(60)

# =============================================
# 🚀 تشغيل البوت المحسن - حل مشكلة 409
# =============================================

def run_bot():
    """تشغيل البوت فقط - بدون تعقيد"""
    print("🔄 Starting USDT Telegram Bot...")
    print(f"✅ BOT_TOKEN: {BOT_TOKEN[:10]}...")
    print("🎯 Bot Features: Games, VIP, Withdraw, Referrals")
    print("🤖 Starting Telegram Bot Polling...")
    
    # تشغيل البوت مباشرة
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60, restart_on_change=True)
    except Exception as e:
        print(f"❌ Bot error: {e}")
        print("🔄 Restarting in 10 seconds...")
        time.sleep(10)
        run_bot()  # إعادة التشغيل التلقائي

if __name__ == "__main__":
    run_bot()
