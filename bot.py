import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random
import json
from datetime import datetime, timedelta

# 🔧 إعدادات البوت
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    exit(1)

print(f"✅ Token loaded: {BOT_TOKEN[:10]}...")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# المشرفين
ADMIN_IDS = [8400225549]

# تخزين البيانات في الذاكرة (مؤقت)
users_db = {}
referrals_db = []
backups_db = []
transactions_db = []

# 🔧 دوال مساعدة
def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {
            'user_id': user_id,
            'username': "",
            'first_name': "",
            'last_name': "",
            'balance': 0.0,
            'referrals_count': 0,
            'referrer_id': None,
            'vip_level': 0,
            'vip_expiry': None,
            'games_played_today': 0,
            'total_games_played': 0,
            'total_earned': 0.0,
            'total_deposits': 0.0,
            'games_counter': 0,
            'last_daily_bonus': None,
            'withdrawal_attempts': 0,
            'new_referrals_count': 0,
            'registration_date': datetime.now().isoformat()
        }
    return users_db[user_id]

def save_user(user_data):
    users_db[user_data['user_id']] = user_data
    return True

def add_balance(user_id, amount, description="", is_deposit=False):
    user = get_user(user_id)
    user['balance'] += amount
    user['total_earned'] += amount
    
    if is_deposit:
        user['total_deposits'] += amount
    
    # تسجيل المعاملة
    transactions_db.append({
        'user_id': user_id,
        'type': 'deposit' if is_deposit else 'bonus',
        'amount': amount,
        'description': description,
        'timestamp': datetime.now().isoformat()
    })
    
    return True

def add_referral(referrer_id, referred_id):
    if referrer_id == referred_id:
        return False
    
    # التحقق من عدم تكرار الإحالة
    for ref in referrals_db:
        if ref['referrer_id'] == referrer_id and ref['referred_id'] == referred_id:
            return False
    
    # إضافة الإحالة
    referrals_db.append({
        'referrer_id': referrer_id,
        'referred_id': referred_id,
        'bonus_given': True,
        'timestamp': datetime.now().isoformat()
    })
    
    # تحديث إحالات المُحيل
    referrer = get_user(referrer_id)
    referrer['referrals_count'] += 1
    
    # منح مكافآت الإحالة
    add_balance(referrer_id, 1.0, f"مكافأة إحالة للمستخدم {referred_id}")
    add_balance(referred_id, 1.0, "مكافأة انضمام بالإحالة")
    
    # إعادة تعيين محاولات الألعاب للمُحيل
    referrer['games_played_today'] = max(0, referrer['games_played_today'] - 1)
    
    return True

# 🛠️ نظام النسخ الاحتياطي
def create_sql_backup():
    try:
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'users': users_db,
            'referrals': referrals_db,
            'total_users': len(users_db),
            'total_referrals': len(referrals_db)
        }
        
        backups_db.append({
            'backup_data': backup_data,
            'created_at': datetime.now().isoformat(),
            'description': f"Backup {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        })
        
        print(f"✅ تم إنشاء نسخة احتياطية: {len(users_db)} مستخدم")
        return True
        
    except Exception as e:
        print(f"❌ فشل النسخ الاحتياطي: {e}")
        return False

def list_sql_backups():
    return backups_db[-10:] if backups_db else []

# 🎯 الأزرار بنفس التصميم الأصلي
def create_main_menu():
    keyboard = [
        [
            InlineKeyboardButton("🎮 الألعاب (3 محاولات)", callback_data="games_menu"),
            InlineKeyboardButton("📊 الملف الشخصي", callback_data="profile")
        ],
        [
            InlineKeyboardButton("👥 الإحالات (+1 محاولة)", callback_data="referral"),
            InlineKeyboardButton("💰 سحب رصيد", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton("🆘 الدعم الفني", url="https://t.me/Trust_wallet_Support_3"),
            InlineKeyboardButton("💎 باقات VIP", callback_data="vip_packages")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_games_menu():
    keyboard = [
        [
            InlineKeyboardButton("🎰 سلوتس", callback_data="game_slots"),
            InlineKeyboardButton("🎲 النرد", callback_data="game_dice")
        ],
        [
            InlineKeyboardButton("⚽ كرة القدم", callback_data="game_football"),
            InlineKeyboardButton("🏀 السلة", callback_data="game_basketball")
        ],
        [
            InlineKeyboardButton("🎯 السهم", callback_data="game_darts"),
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_vip_keyboard():
    keyboard = [
        [InlineKeyboardButton("🟢 برونزي - 5 USDT", callback_data="buy_bronze")],
        [InlineKeyboardButton("🔵 فضى - 10 USDT", callback_data="buy_silver")],
        [InlineKeyboardButton("🟡 ذهبي - 20 USDT", callback_data="buy_gold")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_withdraw_keyboard():
    keyboard = [
        [InlineKeyboardButton("💳 تأكيد استخدام BEP20", callback_data="confirm_bep20")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_referral_keyboard(user_id, bot_username):
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    keyboard = [
        [InlineKeyboardButton("📤 مشاركة الرابط", 
                url=f"https://t.me/share/url?url={referral_link}&text=انضم إلى هذا البوت الرائع واحصل على 1.0 USDT مجاناً! 🎮")],
        [InlineKeyboardButton("🔗 نسخ الرابط", callback_data="copy_link")],
        [InlineKeyboardButton("📊 إحالاتي", callback_data="my_referrals")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
    ]
    
    return InlineKeyboardMarkup(keyboard), referral_link

# 🎮 دوال الألعاب
def play_slots_game(user_id):
    symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎"]
    result = [random.choice(symbols) for _ in range(3)]
    
    # حساب المكافأة
    if result[0] == result[1] == result[2]:
        win_amount = 5.0
    elif result[0] == result[1] or result[1] == result[2]:
        win_amount = 2.0
    else:
        win_amount = 0.0
    
    return result, win_amount

def play_dice_game(user_id):
    user_dice = random.randint(1, 6)
    bot_dice = random.randint(1, 6)
    
    if user_dice > bot_dice:
        result = "فوز"
        win_amount = 3.0
    elif user_dice < bot_dice:
        result = "خسارة" 
        win_amount = 0.0
    else:
        result = "تعادل"
        win_amount = 1.0
    
    return user_dice, bot_dice, result, win_amount

def play_football_game(user_id):
    outcomes = ["هدف 🥅", "إصابة القائم 🚩", "حارس يصد ⛔"]
    result = random.choices(outcomes, k=3)
    win_amount = 2.0 if "هدف" in result else 0.5
    return result, win_amount

def play_basketball_game(user_id):
    shots = []
    goals = 0
    for i in range(3):
        if random.random() > 0.3:
            shot_type = "🎯 تسجيل ✅"
            goals += 1
        else:
            shot_type = "🎯 أخطأت ❌"
        shots.append(shot_type)
    
    win_amount = goals * 1.0
    return shots, win_amount

def play_darts_game(user_id):
    scores = []
    total_score = 0
    for i in range(3):
        score = random.randint(10, 50)
        scores.append(f"🎯 نقاط: {score}")
        total_score += score
    
    win_amount = total_score / 50.0  # 0.2 إلى 1.0 USDT
    return scores, win_amount

# 🎯 الأمر start الأساسي
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user.get('username'):
        referrer_id = None
        referral_bonus = 0
        
        # نظام الإحالات
        if context.args and len(context.args) > 0:
            try:
                referrer_id = int(context.args[0])
                if referrer_id != user_id:
                    if add_referral(referrer_id, user_id):
                        referral_bonus = 1.0
            except:
                referrer_id = None
        
        user_data = {
            'user_id': user_id,
            'username': update.effective_user.username or "",
            'first_name': update.effective_user.first_name or "",
            'last_name': update.effective_user.last_name or "",
            'referrer_id': referrer_id,
            'balance': 0.0 + referral_bonus,
            'games_played_today': 0,
            'total_deposits': 0.0,
            'withdrawal_attempts': 0,
            'new_referrals_count': 0,
            'registration_date': datetime.now().isoformat()
        }
        save_user(user_data)
        user = user_data
        
        welcome_text = f"""
🎮 أهلاً وسهلاً {update.effective_user.first_name}!

🎯 لديك 3 محاولات لعب مجانية
💰 مكافأة الإحالة: 1.0 USDT لكل صديق
👥 كل إحالة تمنحك محاولة إضافية

🏆 اربح 5 USDT كل 3 محاولات!"""
        
        if referral_bonus > 0:
            welcome_text += f"\n\n🎉 حصلت على {referral_bonus} USDT مكافأة انضمام!"
    
    else:
        welcome_text = f"""
🎮 مرحباً بعودتك {update.effective_user.first_name}!

💰 رصيدك: {user['balance']:.1f} USDT
👥 عدد الإحالات: {user['referrals_count']}
🎯 المحاولات المتبقية: {3 - user['games_played_today']}
🏆 مستوى VIP: {user['vip_level']}"""
    
    await update.message.reply_text(welcome_text, reply_markup=create_main_menu())

# 🎯 معالجة الـ Callbacks (الأزرار)
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user(user_id)
    bot_username = context.bot.username
    
    if query.data == "main_menu":
        welcome_text = f"""
🎮 أهلاً {query.from_user.first_name}!

💰 رصيدك: {user['balance']:.1f} USDT
👥 إحالاتك: {user['referrals_count']}
🎯 المحاولات: {3 - user['games_played_today']}/3
💎 مستوى VIP: {user['vip_level']}"""
        
        await query.edit_message_text(
            text=welcome_text,
            reply_markup=create_main_menu()
        )
    
    elif query.data == "games_menu":
        await query.edit_message_text(
            text="🎮 اختر لعبة من القائمة:",
            reply_markup=create_games_menu()
        )
    
    elif query.data == "profile":
        profile_text = f"""
📊 الملف الشخصي:

👤 الاسم: {query.from_user.first_name}
🆔 الآيدي: {user_id}
💰 الرصيد: {user['balance']:.1f} USDT
👥 الإحالات: {user['referrals_count']}
🎯 المحاولات: {3 - user['games_played_today']}/3
💎 VIP: {user['vip_level']}
🏆 الألعاب: {user['total_games_played']}
💳 الإيداعات: {user['total_deposits']:.1f} USDT"""
        
        await query.edit_message_text(
            text=profile_text,
            reply_markup=create_main_menu()
        )
    
    elif query.data == "referral":
        keyboard, referral_link = create_referral_keyboard(user_id, bot_username)
        referral_text = f"""
👥 نظام الإحالات:

💰 احصل على 1.0 USDT لكل صديق
🎯 واحصل على محاولة لعب إضافية

🔗 رابط الإحالة الخاص بك:
{referral_link}

📊 لديك {user['referrals_count']} إحالة"""
        
        await query.edit_message_text(
            text=referral_text,
            reply_markup=keyboard
        )
    
    elif query.data == "vip_packages":
        vip_text = """
💎 باقات VIP:

🟢 برونزي - 5 USDT
• محاولات لعب غير محدودة
• مكافآت مضاعفة

🔵 فضى - 10 USDT  
• كل مزايا البرونزي
• دعم فني متميز

🟡 ذهبي - 20 USDT
• كل المزايا السابقة
• أولوية في السحب"""
        
        await query.edit_message_text(
            text=vip_text,
            reply_markup=create_vip_keyboard()
        )
    
    elif query.data == "withdraw":
        withdraw_text = f"""
💰 سحب رصيد:

💳 الحد الأدنى للسحب: 10 USDT
🔄 استخدام شبكة BEP20

💰 رصيدك الحالي: {user['balance']:.1f} USDT"""
        
        if user['balance'] >= 10:
            await query.edit_message_text(
                text=withdraw_text + "\n\n✅ يمكنك سحب رصيدك الآن!",
                reply_markup=create_withdraw_keyboard()
            )
        else:
            await query.edit_message_text(
                text=withdraw_text + f"\n\n❌ تحتاج {10 - user['balance']:.1f} USDT أخرى للسحب",
                reply_markup=create_main_menu()
            )
    
    elif query.data.startswith("game_"):
        game_type = query.data.replace("game_", "")
        
        # التحقق من المحاولات
        if user['games_played_today'] >= 3:
            await query.answer("❌ انتهت محاولاتك اليوم! جددها بالإحالات", show_alert=True)
            return
        
        # زيادة عداد الألعاب
        user['games_played_today'] += 1
        user['total_games_played'] += 1
        user['games_counter'] += 1
        
        # تشغيل اللعبة
        if game_type == "slots":
            result, win_amount = play_slots_game(user_id)
            game_result = f"🎰 نتيجة السلوتس: {' '.join(result)}"
        elif game_type == "dice":
            user_dice, bot_dice, result, win_amount = play_dice_game(user_id)
            game_result = f"🎲 النرد: أنت {user_dice} vs البوت {bot_dice} - {result}"
        elif game_type == "football":
            result, win_amount = play_football_game(user_id)
            game_result = f"⚽ كرة القدم: {' | '.join(result)}"
        elif game_type == "basketball":
            result, win_amount = play_basketball_game(user_id)
            game_result = f"🏀 السلة: {' | '.join(result)}"
        elif game_type == "darts":
            result, win_amount = play_darts_game(user_id)
            game_result = f"🎯 السهم: {' | '.join(result)}"
        else:
            game_result = f"🎮 لعبة {game_type}"
            win_amount = 0
        
        # منح المكافأة
        if win_amount > 0:
            add_balance(user_id, win_amount, f"ربح لعبة {game_type}")
            win_text = f"🎉 ربحت {win_amount} USDT!"
        else:
            win_text = "😔 لم تربح هذه المرة"
        
        # مكافأة كل 3 محاولات
        if user['games_counter'] >= 3:
            bonus_amount = 5.0
            add_balance(user_id, bonus_amount, "مكافأة كل 3 محاولات")
            user['games_counter'] = 0
            bonus_text = f"\n🏆 مبروك! حصلت على مكافأة {bonus_amount} USDT لكل 3 محاولات!"
        else:
            bonus_text = ""
        
        remaining = 3 - user['games_played_today']
        result_text = f"""
{game_result}

{win_text}
{bonus_text}

🎯 المحاولات المتبقية: {remaining}/3
💰 الرصيد: {user['balance']:.1f} USDT"""
        
        await query.edit_message_text(
            text=result_text,
            reply_markup=create_games_menu()
        )
    
    elif query.data in ["buy_bronze", "buy_silver", "buy_gold"]:
        vip_data = {
            "buy_bronze": {"name": "برونزي", "price": 5.0, "level": 1},
            "buy_silver": {"name": "فضى", "price": 10.0, "level": 2},
            "buy_gold": {"name": "ذهبي", "price": 20.0, "level": 3}
        }
        
        vip_info = vip_data[query.data]
        
        if user['balance'] >= vip_info['price']:
            # خصم السعر
            user['balance'] -= vip_info['price']
            user['vip_level'] = vip_info['level']
            user['vip_expiry'] = (datetime.now() + timedelta(days=30)).isoformat()
            
            await query.answer(f"✅ تم شراء باقة {vip_info['name']} بنجاح!", show_alert=True)
            await query.edit_message_text(
                text=f"✅ تم تفعيل باقة {vip_info['name']} VIP!\n\n💰 الرصيد المتبقي: {user['balance']:.1f} USDT",
                reply_markup=create_main_menu()
            )
        else:
            await query.answer(f"❌ رصيدك غير كافٍ! تحتاج {vip_info['price']} USDT", show_alert=True)
    
    elif query.data == "confirm_bep20":
        if user['balance'] >= 10:
            # محاكاة عملية السحب
            user['withdrawal_attempts'] += 1
            await query.answer("✅ تم استلام طلب السحب بنجاح!", show_alert=True)
            await query.edit_message_text(
                text=f"✅ تم استلام طلب سحب {user['balance']:.1f} USDT\n\n📧 سيتم التواصل معك خلال 24 ساعة",
                reply_markup=create_main_menu()
            )
        else:
            await query.answer("❌ الرصيد غير كافٍ للسحب!", show_alert=True)
    
    elif query.data == "copy_link":
        await query.answer("✅ تم نسخ رابط الإحالة إلى الحافظة", show_alert=True)
    
    elif query.data == "my_referrals":
        await query.answer(f"📊 لديك {user['referrals_count']} إحالة", show_alert=True)

# 🛠️ الأوامر الإدارية المتقدمة
async def quick_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 2:
            await update.message.reply_text("❌ استخدم: /quickadd [user_id] [amount]")
            return
        
        target_user_id = int(context.args[0])
        amount = float(context.args[1])
        
        if add_balance(target_user_id, amount, f"إضافة إدارية بواسطة {update.effective_user.id}", is_deposit=True):
            user = get_user(target_user_id)
            response = f"✅ تم إضافة {amount} USDT للمستخدم {target_user_id}\n💰 الرصيد الجديد: {user['balance']:.1f} USDT"
            
            # إشعار المستخدم
            try:
                await context.bot.send_message(target_user_id, f"🎉 تم إضافة {amount} USDT إلى رصيدك!\n💰 رصيدك الحالي: {user['balance']:.1f} USDT")
            except:
                pass
        else:
            response = "❌ فشل في إضافة الرصيد"
        
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def set_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 2:
            await update.message.reply_text("❌ استخدم: /setbalance [user_id] [amount]")
            return
        
        target_user_id = int(context.args[0])
        amount = float(context.args[1])
        
        user = get_user(target_user_id)
        old_balance = user['balance']
        user['balance'] = amount
        
        response = f"✅ تم تعيين رصيد المستخدم {target_user_id}\n💰 الرصيد السابق: {old_balance:.1f} USDT\n💰 الرصيد الجديد: {user['balance']:.1f} USDT"
        await update.message.reply_text(response)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def set_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 2:
            await update.message.reply_text("❌ استخدم: /setreferrals [user_id] [count]")
            return
        
        target_user_id = int(context.args[0])
        count = int(context.args[1])
        
        user = get_user(target_user_id)
        old_count = user['referrals_count']
        user['referrals_count'] = count
        
        response = f"✅ تم تعيين إحالات المستخدم {target_user_id}\n👥 الإحالات السابقة: {old_count}\n👥 الإحالات الجديدة: {user['referrals_count']}"
        await update.message.reply_text(response)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def set_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 2:
            await update.message.reply_text("❌ استخدم: /setdeposits [user_id] [amount]")
            return
        
        target_user_id = int(context.args[0])
        amount = float(context.args[1])
        
        user = get_user(target_user_id)
        old_deposits = user['total_deposits']
        user['total_deposits'] = amount
        
        response = f"✅ تم تعيين إيداعات المستخدم {target_user_id}\n💳 الإيداعات السابقة: {old_deposits:.1f} USDT\n💳 الإيداعات الجديدة: {user['total_deposits']:.1f} USDT"
        await update.message.reply_text(response)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def set_games_attempts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 2:
            await update.message.reply_text("❌ استخدم: /setattempts [user_id] [attempts]")
            return
        
        target_user_id = int(context.args[0])
        attempts = int(context.args[1])
        
        user = get_user(target_user_id)
        old_attempts = user['games_played_today']
        user['games_played_today'] = attempts
        
        response = f"✅ تم تعيين محاولات المستخدم {target_user_id}\n🎯 المحاولات السابقة: {old_attempts}/3\n🎯 المحاولات الجديدة: {user['games_played_today']}/3"
        await update.message.reply_text(response)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def reset_attempts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 1:
            await update.message.reply_text("❌ استخدم: /resetattempts [user_id]")
            return
        
        target_user_id = int(context.args[0])
        
        user = get_user(target_user_id)
        user['games_played_today'] = 0
        
        response = f"✅ تم إعادة تعيين محاولات المستخدم {target_user_id}\n🎯 الآن لديه 3/3 محاولات"
        await update.message.reply_text(response)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def set_vip_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 2:
            await update.message.reply_text("❌ استخدم: /setvip [user_id] [level]")
            return
        
        target_user_id = int(context.args[0])
        level = int(context.args[1])
        
        user = get_user(target_user_id)
        old_level = user['vip_level']
        user['vip_level'] = level
        user['vip_expiry'] = (datetime.now() + timedelta(days=30)).isoformat()
        
        response = f"✅ تم تعيين مستوى VIP للمستخدم {target_user_id}\n💎 المستوى السابق: {old_level}\n💎 المستوى الجديد: {user['vip_level']}"
        await update.message.reply_text(response)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def user_full_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(context.args) != 1:
            await update.message.reply_text("❌ استخدم: /userinfo [user_id]")
            return
        
        user_id = int(context.args[0])
        user = get_user(user_id)
        
        if user:
            remaining_games = 3 - user['games_played_today']
            vip_expiry = user['vip_expiry'][:10] if user['vip_expiry'] else "غير محدد"
            reg_date = user['registration_date'][:10] if 'registration_date' in user else "غير معروف"
            
            info_text = f"""
📊 معلومات كاملة عن المستخدم:

🆔 الآيدي: {user['user_id']}
👤 الاسم: {user['first_name']} {user.get('last_name', '')}

💰 الحساب المالي:
• الرصيد: {user['balance']:.1f} USDT
• إجمالي الإيداعات: {user['total_deposits']:.1f} USDT
• إجمالي الأرباح: {user['total_earned']:.1f} USDT

🎮 إحصائيات الألعاب:
• المحاولات المتبقية: {remaining_games}/3
• إجمالي الألعاب: {user['total_games_played']}
• عداد المكافآت: {user['games_counter']}/3

👥 نظام الإحالات:
• عدد الإحالات: {user['referrals_count']}
• محاولات السحب: {user['withdrawal_attempts']}

💎 معلومات VIP:
• المستوى: {user['vip_level']}
• انتهاء الصلاحية: {vip_expiry}

📅 معلومات عامة:
• تاريخ التسجيل: {reg_date}"""
        else:
            info_text = "❌ المستخدم غير موجود!"
        
        await update.message.reply_text(info_text)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ ليس لديك صلاحية لهذا الأمر!")
        return
    
    try:
        if len(users_db) == 0:
            await update.message.reply_text("❌ لا يوجد مستخدمين في قاعدة البيانات")
            return
        
        users_list = "📊 قائمة المستخدمين:\n\n"
        for i, (user_id, user_data) in enumerate(list(users_db.items())[:20], 1):
            users_list += f"{i}. {user_data['first_name']} - {user_id} - {user_data['balance']:.1f} USDT - {user_data['referrals_count']} إحالة\n"
        
        if len(users_db) > 20:
            users_list += f"\n📎 وإجمالي {len(users_db)} مستخدم"
        
        await update.message.reply_text(users_list)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 معرفك: `{update.effective_user.id}`")

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ البوت يعمل! جرب الأزرار في القائمة الرئيسية")

def main():
    try:
        print("🔄 Starting bot...")
        application = Application.builder().token(BOT_TOKEN).build()
        
        # إضافة handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("quickadd", quick_add_balance))
        application.add_handler(CommandHandler("setbalance", set_balance))
        application.add_handler(CommandHandler("setreferrals", set_referrals))
        application.add_handler(CommandHandler("setdeposits", set_deposits))
        application.add_handler(CommandHandler("setattempts", set_games_attempts))
        application.add_handler(CommandHandler("resetattempts", reset_attempts))
        application.add_handler(CommandHandler("setvip", set_vip_level))
        application.add_handler(CommandHandler("userinfo", user_full_info))
        application.add_handler(CommandHandler("listusers", list_users))
        application.add_handler(CommandHandler("myid", myid_command))
        application.add_handler(CommandHandler("test", test_command))
        application.add_handler(CallbackQueryHandler(handle_callbacks))
        
        print("✅ Bot is running and ready to receive messages...")
        print("🎮 Features: Games, Referrals, VIP, Withdrawals, Admin Commands")
        print("🛠️ Admin Commands Available:")
        print("   /quickadd [user_id] [amount] - إضافة رصيد")
        print("   /setbalance [user_id] [amount] - تعيين رصيد")
        print("   /setreferrals [user_id] [count] - تعيين الإحالات")
        print("   /setdeposits [user_id] [amount] - تعيين الإيداعات")
        print("   /setattempts [user_id] [attempts] - تعيين المحاولات")
        print("   /resetattempts [user_id] - إعادة تعيين المحاولات")
        print("   /setvip [user_id] [level] - تعيين مستوى VIP")
        print("   /userinfo [user_id] - معلومات المستخدم")
        print("   /listusers - قائمة المستخدمين")
        
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == '__main__':
    main()
