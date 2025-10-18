# ======================
# 🛠️ الأوامر الإدارية - بنفس الصيغة المطلوبة
# ======================

@bot.message_handler(commands=['quickadd'])
def handle_quickadd(message):
    """💰 إضافة رصيد - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /quickadd [user_id] [amount]")
            return
        
        target_user_id = parts[1]
        amount = float(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        new_balance = user['balance'] + amount
        success = update_user(target_user_id, balance=new_balance)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم إضافة {amount} USDT للمستخدم {target_user_id}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إضافة الرصيد!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setbalance'])
def handle_setbalance(message):
    """💰 تعيين رصيد محدد - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /setbalance [user_id] [amount]")
            return
        
        target_user_id = parts[1]
        amount = float(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        success = update_user(target_user_id, balance=amount)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين رصيد المستخدم {target_user_id} إلى {amount} USDT")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين الرصيد!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setreferrals'])
def handle_setreferrals(message):
    """👥 تعيين عدد الإحالات - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /setreferrals [user_id] [count]")
            return
        
        target_user_id = parts[1]
        count = int(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        success = update_user(target_user_id, referral_count=count)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين إحالات المستخدم {target_user_id} إلى {count}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين الإحالات!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['addreferral'])
def handle_addreferral(message):
    """👥 إضافة إحالة واحدة - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "📝 usage: /addreferral [user_id]")
            return
        
        target_user_id = parts[1]
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        new_count = user['referral_count'] + 1
        success = update_user(target_user_id, referral_count=new_count)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم إضافة إحالة للمستخدم {target_user_id}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إضافة الإحالة!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setattempts'])
def handle_setattempts(message):
    """🎯 تعيين محاولات الألعاب - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /setattempts [user_id] [attempts]")
            return
        
        target_user_id = parts[1]
        attempts = int(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        success = update_user(target_user_id, attempts=attempts)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين محاولات المستخدم {target_user_id} إلى {attempts}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين المحاولات!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['resetattempts'])
def handle_resetattempts(message):
    """🎯 إعادة تعيين المحاولات - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "📝 usage: /resetattempts [user_id]")
            return
        
        target_user_id = parts[1]
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        vip_info = VIP_LEVELS[user['vip_level']]
        base_attempts = vip_info['max_attempts']
        
        success = update_user(target_user_id, attempts=base_attempts)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم إعادة تعيين محاولات المستخدم {target_user_id} إلى {base_attempts}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إعادة تعيين المحاولات!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['addattempts'])
def handle_addattempts(message):
    """🎯 إضافة محاولات - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /addattempts [user_id] [count]")
            return
        
        target_user_id = parts[1]
        count = int(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        new_attempts = user['attempts'] + count
        success = update_user(target_user_id, attempts=new_attempts)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم إضافة {count} محاولة للمستخدم {target_user_id}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إضافة المحاولات!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setdeposits'])
def handle_setdeposits(message):
    """💳 تعيين إجمالي الإيداعات - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /setdeposits [user_id] [amount]")
            return
        
        target_user_id = parts[1]
        amount = float(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        success = update_user(target_user_id, total_deposits=amount)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين إيداعات المستخدم {target_user_id} إلى {amount} USDT")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين الإيداعات!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['adddeposit'])
def handle_adddeposit(message):
    """💳 إضافة إيداع - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /adddeposit [user_id] [amount]")
            return
        
        target_user_id = parts[1]
        amount = float(parts[2])
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        new_deposits = user['total_deposits'] + amount
        success = update_user(target_user_id, total_deposits=new_deposits)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم إضافة إيداع {amount} USDT للمستخدم {target_user_id}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في إضافة الإيداع!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['userinfo'])
def handle_userinfo(message):
    """📊 معلومات كاملة عن المستخدم - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "📝 usage: /userinfo [user_id]")
            return
        
        target_user_id = parts[1]
        user = get_user(target_user_id)
        
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        vip_info = VIP_LEVELS[user['vip_level']]
        
        info_msg = f"👤 معلومات المستخدم:\n\n"
        info_msg += f"🆔 المعرف: {user['user_id']}\n"
        info_msg += f"👤 الاسم: {user['first_name'] or 'غير معروف'}\n"
        info_msg += f"💰 الرصيد: {user['balance']:.2f} USDT\n"
        info_msg += f"👥 الإحالات: {user['referral_count']}\n"
        info_msg += f"🏆 مستوى VIP: {vip_info['name']}\n"
        info_msg += f"🎯 المحاولات: {user['attempts']}\n"
        info_msg += f"💎 إجمالي الأرباح: {user['total_earnings']:.2f} USDT\n"
        info_msg += f"💳 إجمالي الإيداعات: {user['total_deposits']:.2f} USDT\n"
        info_msg += f"📅 تاريخ التسجيل: {user['registration_date']}"
        
        bot.send_message(message.chat.id, info_msg)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['listusers'])
def handle_listusers(message):
    """📊 قائمة جميع المستخدمين - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        conn = get_db_connection()
        if not conn:
            bot.send_message(message.chat.id, "❌ خطأ في قاعدة البيانات!")
            return
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()['total']
        
        cursor.execute("SELECT user_id, first_name, balance FROM users ORDER BY registration_date DESC LIMIT 20")
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            bot.send_message(message.chat.id, "❌ لا يوجد مستخدمين!")
            return
        
        users_msg = f"👥 قائمة المستخدمين (آخر 20 من أصل {total_users}):\n\n"
        
        for i, user in enumerate(users, 1):
            users_msg += f"{i}. {user['first_name'] or 'غير معروف'} (ID: {user['user_id']})\n"
            users_msg += f"   💰 {user['balance']:.2f} USDT\n\n"
        
        bot.send_message(message.chat.id, users_msg)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['stats'])
def handle_stats(message):
    """📊 إحصائيات البوت - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        conn = get_db_connection()
        if not conn:
            bot.send_message(message.chat.id, "❌ خطأ في قاعدة البيانات!")
            return
        
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total_users FROM users")
        total_users = cursor.fetchone()['total_users']
        
        cursor.execute("SELECT SUM(balance) as total_balance FROM users")
        total_balance = cursor.fetchone()['total_balance'] or 0
        
        cursor.execute("SELECT SUM(total_earnings) as total_earnings FROM users")
        total_earnings = cursor.fetchone()['total_earnings'] or 0
        
        cursor.execute("SELECT SUM(total_deposits) as total_deposits FROM users")
        total_deposits = cursor.fetchone()['total_deposits'] or 0
        
        cursor.execute("SELECT SUM(referral_count) as total_referrals FROM users")
        total_referrals = cursor.fetchone()['total_referrals'] or 0
        
        conn.close()
        
        stats_msg = "📊 إحصائيات البوت:\n\n"
        stats_msg += f"👥 إجمالي المستخدمين: {total_users}\n"
        stats_msg += f"💰 إجمالي الرصيد: {total_balance:.2f} USDT\n"
        stats_msg += f"💎 إجمالي الأرباح: {total_earnings:.2f} USDT\n"
        stats_msg += f"💳 إجمالي الإيداعات: {total_deposits:.2f} USDT\n"
        stats_msg += f"👥 إجمالي الإحالات: {total_referrals}"
        
        bot.send_message(message.chat.id, stats_msg)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['setvip'])
def handle_setvip(message):
    """💎 تعيين مستوى VIP - للمشرفين فقط"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "📝 usage: /setvip [user_id] [level]")
            return
        
        target_user_id = parts[1]
        vip_level = int(parts[2])
        
        if vip_level not in VIP_LEVELS:
            bot.send_message(message.chat.id, "❌ مستوى VIP غير صحيح! استخدم الأرقام من 0 إلى 4")
            return
        
        user = get_user(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود!")
            return
        
        vip_info = VIP_LEVELS[vip_level]
        success = update_user(target_user_id, vip_level=vip_level)
        
        if success:
            bot.send_message(message.chat.id, f"✅ تم تعيين مستوى VIP للمستخدم {target_user_id} إلى {vip_info['name']}")
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعيين مستوى VIP!")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")
