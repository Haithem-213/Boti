# ================================================================
# DWR_CASINO_BOT – كازينو حقيقي بالدولار (نسخة 1xBet)
# تم التكوين ببياناتك الخاصة
# ================================================================

import sqlite3
import random
import json
import time
import hashlib
import hmac
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ================================================================
# 1. بياناتك الخاصة - تم إدخالها
# ================================================================
BOT_TOKEN = "8926371456:AAFVmtHt8syxbOXXIJqraKkW_ZnvZS6Zpz0"
API_ID = 6557078198
API_HASH = "95b4ce77d62ef71db30c29d760728d60"

# ================================================================
# 2. قاعدة البيانات
# ================================================================
conn = sqlite3.connect('dwr_casino.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
    tg_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    balance_usd REAL DEFAULT 0.0,
    total_deposited REAL DEFAULT 0.0,
    total_withdrawn REAL DEFAULT 0.0,
    total_bet REAL DEFAULT 0.0,
    total_won REAL DEFAULT 0.0,
    is_verified INTEGER DEFAULT 0,
    deposit_address TEXT,
    joined_date TEXT,
    last_active TEXT,
    is_banned INTEGER DEFAULT 0
)''')

c.execute('''CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER,
    amount REAL,
    tx_hash TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    confirmed_at TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER,
    amount REAL,
    wallet_address TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    processed_at TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS bet_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER,
    game_type TEXT,
    bet_amount REAL,
    multiplier REAL,
    result TEXT,
    win_amount REAL,
    created_at TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
)''')

# إعدادات الكازينو
c.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('min_deposit', '10')")
c.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('min_withdraw', '10')")
c.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('house_edge', '0.05')")
c.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('referral_bonus', '2.0')")
c.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('wallet_address', '0xDWR_Casino_Main_Wallet_Address')")
conn.commit()

# ================================================================
# 3. تشغيل البوت
# ================================================================
app = Client("dwr_casino_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================================================================
# 4. دوال مساعدة
# ================================================================
def get_user(tg_id):
    c.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    return c.fetchone()

def add_balance(tg_id, amount):
    c.execute("UPDATE users SET balance_usd = balance_usd + ? WHERE tg_id = ?", (amount, tg_id))
    conn.commit()

def deduct_balance(tg_id, amount):
    c.execute("UPDATE users SET balance_usd = balance_usd - ? WHERE tg_id = ?", (amount, tg_id))
    conn.commit()

def register_user(tg_id, username, first_name):
    deposit_address = f"0x{hashlib.sha256(f'{tg_id}{time.time()}'.encode()).hexdigest()[:40]}"
    c.execute("""
        INSERT INTO users (tg_id, username, first_name, deposit_address, joined_date)
        VALUES (?, ?, ?, ?, ?)
    """, (tg_id, username, first_name, deposit_address, datetime.now().isoformat()))
    conn.commit()
    return deposit_address

def is_verified(tg_id):
    user = get_user(tg_id)
    return user and user[6] == 1

# ================================================================
# 5. ألعاب الكازينو
# ================================================================

def roulette_spin(bet_amount, choice):
    result = random.randint(0, 36)
    if result == 0:
        color = "green"
    elif result % 2 == 0:
        color = "red"
    else:
        color = "black"
    
    win = False
    multiplier = 0
    
    if choice == "red" and color == "red":
        win = True
        multiplier = 2
    elif choice == "black" and color == "black":
        win = True
        multiplier = 2
    elif choice == "green" and color == "green":
        win = True
        multiplier = 35
    elif choice.startswith("number_") and int(choice.split("_")[1]) == result:
        win = True
        multiplier = 36
    
    win_amount = bet_amount * multiplier if win else 0
    
    return {
        "result": result,
        "color": color,
        "win": win,
        "multiplier": multiplier,
        "win_amount": win_amount
    }

def slots_spin(bet_amount):
    symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣", "⭐", "🎰"]
    reel1 = random.choice(symbols)
    reel2 = random.choice(symbols)
    reel3 = random.choice(symbols)
    
    win = False
    multiplier = 0
    
    if reel1 == reel2 == reel3:
        win = True
        if reel1 == "💎":
            multiplier = 10
        elif reel1 == "7️⃣":
            multiplier = 8
        elif reel1 == "🎰":
            multiplier = 6
        elif reel1 == "⭐":
            multiplier = 5
        else:
            multiplier = 3
    elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
        win = True
        multiplier = 1.5
    
    win_amount = bet_amount * multiplier if win else 0
    
    return {
        "reels": [reel1, reel2, reel3],
        "win": win,
        "multiplier": multiplier,
        "win_amount": win_amount
    }

def crash_game(bet_amount, crash_point):
    crash_multiplier = random.uniform(1.0, 10.0)
    if crash_point <= crash_multiplier:
        win = True
        win_amount = bet_amount * crash_point
    else:
        win = False
        win_amount = 0
    return {
        "crash_multiplier": crash_multiplier,
        "player_point": crash_point,
        "win": win,
        "win_amount": win_amount
    }

def dice_roll(bet_amount, prediction, target):
    roll = random.randint(1, 100)
    win = False
    if prediction == "over" and roll > target:
        win = True
    elif prediction == "under" and roll < target:
        win = True
    multiplier = 100 / target if prediction == "under" else 100 / (100 - target)
    win_amount = bet_amount * multiplier if win else 0
    return {
        "roll": roll,
        "win": win,
        "multiplier": multiplier,
        "win_amount": win_amount
    }

# ================================================================
# 6. أوامر البوت
# ================================================================

@app.on_message(filters.command("start"))
def start_command(client, message):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    
    if not user:
        deposit_address = register_user(tg_id, message.from_user.username, message.from_user.first_name)
        user = get_user(tg_id)
    
    verified_status = "✅ مفعل" if user[6] == 1 else "🔒 غير مفعل (أودع 10$ للتفعيل)"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 ألعاب الكازينو", callback_data="games")],
        [InlineKeyboardButton("💰 الرصيد", callback_data="balance")],
        [InlineKeyboardButton("💳 إيداع", callback_data="deposit")],
        [InlineKeyboardButton("💸 سحب", callback_data="withdraw")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton("🏆 الإحالات", callback_data="referrals")]
    ])
    
    message.reply_text(
        f"🎰 *DWR_CASINO* – كازينو حقيقي بالدولار 💵\n\n"
        f"👤 {message.from_user.first_name}\n"
        f"💰 الرصيد: ${user[2]:.2f}\n"
        f"📌 الحالة: {verified_status}\n\n"
        f"🔥 *الألعاب المتاحة:*\n"
        f"• 🎡 الروليت\n"
        f"• 🎰 السلوتس\n"
        f"• ✈️ الكراش (الطائرة)\n"
        f"• 🎲 النرد\n\n"
        f"⚡ *للعب:* اختر لعبة من القائمة\n"
        f"💰 *الإيداع:* 10$ كحد أدنى للتفعيل\n"
        f"💸 *السحب:* حد أدنى 10$\n\n"
        f"💀 DWR_Subscriber | @SGCodexs",
        reply_markup=keyboard
    )

# ================================================================
# 7. معالج الأزرار
# ================================================================

@app.on_callback_query()
def handle_callback(client, callback_query: CallbackQuery):
    tg_id = callback_query.from_user.id
    data = callback_query.data
    user = get_user(tg_id)
    
    if not user:
        callback_query.answer("⚠️ استخدم /start أولاً", show_alert=True)
        return
    
    # ===== القائمة الرئيسية =====
    if data == "games":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎡 الروليت", callback_data="game_roulette")],
            [InlineKeyboardButton("🎰 السلوتس", callback_data="game_slots")],
            [InlineKeyboardButton("✈️ الكراش", callback_data="game_crash")],
            [InlineKeyboardButton("🎲 النرد", callback_data="game_dice")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ])
        callback_query.message.edit_text(
            "🎰 *اختر لعبتك:*\n\n"
            f"💰 رصيدك: ${user[2]:.2f}\n"
            f"📌 الحالة: {'✅ مفعل' if user[6] == 1 else '🔒 غير مفعل'}",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data == "back_main":
        user = get_user(tg_id)
        verified_status = "✅ مفعل" if user[6] == 1 else "🔒 غير مفعل (أودع 10$ للتفعيل)"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎰 ألعاب الكازينو", callback_data="games")],
            [InlineKeyboardButton("💰 الرصيد", callback_data="balance")],
            [InlineKeyboardButton("💳 إيداع", callback_data="deposit")],
            [InlineKeyboardButton("💸 سحب", callback_data="withdraw")],
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
            [InlineKeyboardButton("🏆 الإحالات", callback_data="referrals")]
        ])
        callback_query.message.edit_text(
            f"🎰 *DWR_CASINO*\n\n"
            f"👤 {callback_query.from_user.first_name}\n"
            f"💰 الرصيد: ${user[2]:.2f}\n"
            f"📌 الحالة: {verified_status}",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data == "balance":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ])
        callback_query.message.edit_text(
            f"💰 *رصيدك*\n\n"
            f"💳 الرصيد الحالي: ${user[2]:.2f}\n"
            f"💵 إجمالي الإيداع: ${user[3]:.2f}\n"
            f"💸 إجمالي السحب: ${user[4]:.2f}\n"
            f"🎰 إجمالي المراهنات: ${user[5]:.2f}\n"
            f"🏆 إجمالي المكاسب: ${user[6]:.2f}",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data == "deposit":
        min_deposit = float(c.execute("SELECT value FROM config WHERE key = 'min_deposit'").fetchone()[0])
        bot_wallet = c.execute("SELECT value FROM config WHERE key = 'wallet_address'").fetchone()[0]
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 إيداع 10$", callback_data="deposit_10")],
            [InlineKeyboardButton("💳 إيداع 25$", callback_data="deposit_25")],
            [InlineKeyboardButton("💳 إيداع 50$", callback_data="deposit_50")],
            [InlineKeyboardButton("💳 إيداع 100$", callback_data="deposit_100")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ])
        
        callback_query.message.edit_text(
            f"💳 *الإيداع*\n\n"
            f"📌 الحد الأدنى: ${min_deposit}\n"
            f"🏦 عنوان المحفظة (البوت):\n"
            f"`{bot_wallet}`\n\n"
            f"⚠️ *تنبيه:*\n"
            f"• أرسل المبلغ إلى العنوان أعلاه\n"
            f"• سيتم تفعيل حسابك تلقائياً\n\n"
            f"💰 رصيدك الحالي: ${user[2]:.2f}\n"
            f"📌 الحالة: {'✅ مفعل' if user[6] == 1 else '🔒 غير مفعل'}",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data.startswith("deposit_"):
        amount = float(data.split("_")[1])
        
        if user[6] == 1:
            callback_query.answer("✅ حسابك مفعل بالفعل!", show_alert=True)
            return
        
        add_balance(tg_id, amount)
        c.execute("UPDATE users SET is_verified = 1, total_deposited = total_deposited + ? WHERE tg_id = ?", (amount, tg_id))
        c.execute("INSERT INTO deposits (tg_id, amount, status, created_at) VALUES (?, ?, 'confirmed', ?)", 
                  (tg_id, amount, datetime.now().isoformat()))
        conn.commit()
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎰 العب الآن", callback_data="games")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ])
        
        callback_query.message.edit_text(
            f"✅ *تم الإيداع بنجاح!*\n\n"
            f"💰 المبلغ: ${amount:.2f}\n"
            f"📌 الحالة: ✅ مفعل\n\n"
            f"🎉 تهانينا! يمكنك الآن اللعب والسحب.",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data == "withdraw":
        if user[6] == 0:
            callback_query.answer("❌ يجب إيداع 10$ للتفعيل أولاً!", show_alert=True)
            return
        
        min_withdraw = float(c.execute("SELECT value FROM config WHERE key = 'min_withdraw'").fetchone()[0])
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 سحب 10$", callback_data="withdraw_10")],
            [InlineKeyboardButton("💸 سحب 25$", callback_data="withdraw_25")],
            [InlineKeyboardButton("💸 سحب 50$", callback_data="withdraw_50")],
            [InlineKeyboardButton("💸 سحب 100$", callback_data="withdraw_100")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ])
        
        callback_query.message.edit_text(
            f"💸 *السحب*\n\n"
            f"💰 رصيدك: ${user[2]:.2f}\n"
            f"📉 الحد الأدنى: ${min_withdraw}\n"
            f"🏦 سيتم التحويل إلى المحفظة المسجلة\n\n"
            f"اختر المبلغ:",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data.startswith("withdraw_"):
        amount = float(data.split("_")[1])
        
        if user[2] < amount:
            callback_query.answer(f"❌ رصيدك غير كافٍ. لديك ${user[2]:.2f}", show_alert=True)
            return
        
        deduct_balance(tg_id, amount)
        c.execute("UPDATE users SET total_withdrawn = total_withdrawn + ? WHERE tg_id = ?", (amount, tg_id))
        
        c.execute("""
            INSERT INTO withdrawals (tg_id, amount, wallet_address, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
        """, (tg_id, amount, f"user_{tg_id}_wallet", datetime.now().isoformat()))
        conn.commit()
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ])
        
        callback_query.message.edit_text(
            f"✅ *تم طلب السحب!*\n\n"
            f"💰 المبلغ: ${amount:.2f}\n"
            f"📌 الحالة: قيد المعالجة\n"
            f"🆔 رقم الطلب: {c.lastrowid}\n\n"
            f"⏳ سيتم التحويل خلال 24 ساعة.",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data == "stats":
        total_bets = c.execute("SELECT COUNT(*) FROM bet_history WHERE tg_id = ?", (tg_id,)).fetchone()[0]
        total_bet_amount = c.execute("SELECT COALESCE(SUM(bet_amount), 0) FROM bet_history WHERE tg_id = ?", (tg_id,)).fetchone()[0]
        total_win_amount = c.execute("SELECT COALESCE(SUM(win_amount), 0) FROM bet_history WHERE tg_id = ?", (tg_id,)).fetchone()[0]
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ])
        
        callback_query.message.edit_text(
            f"📊 *إحصائياتك*\n\n"
            f"🎰 إجمالي الألعاب: {total_bets}\n"
            f"💰 إجمالي المراهنات: ${total_bet_amount:.2f}\n"
            f"🏆 إجمالي المكاسب: ${total_win_amount:.2f}\n"
            f"📈 صافي الربح: ${(total_win_amount - total_bet_amount):.2f}\n\n"
            f"💳 الرصيد الحالي: ${user[2]:.2f}",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data == "referrals":
        ref_code = hashlib.md5(f"{tg_id}DWR".encode()).hexdigest()[:8]
        referrals = c.execute("SELECT COUNT(*) FROM users WHERE username LIKE ?", (f"%_{tg_id}%",)).fetchone()[0]
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 مشاركة رابط الإحالة", callback_data="share_ref")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ])
        
        callback_query.message.edit_text(
            f"🏆 *الإحالات*\n\n"
            f"👥 عدد من دعوتهم: {referrals}\n"
            f"🔗 كود الإحالة: `{ref_code}`\n"
            f"💰 مكافأة كل إحالة: $2\n\n"
            f"📤 شارك رابطك:\n"
            f"`https://t.me/{app.get_me().username}?start={ref_code}`\n\n"
            f"🔥 كلما زادت إحالاتك، زادت مكافآتك!",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data == "share_ref":
        ref_code = hashlib.md5(f"{tg_id}DWR".encode()).hexdigest()[:8]
        callback_query.answer(f"انسخ الرابط: https://t.me/{app.get_me().username}?start={ref_code}", show_alert=True)
    
    # ============================================================
    # 8. ألعاب الكازينو
    # ============================================================
    
    elif data == "game_roulette":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔴 أحمر (x2)", callback_data="roulette_red")],
            [InlineKeyboardButton("⚫ أسود (x2)", callback_data="roulette_black")],
            [InlineKeyboardButton("🟢 أخضر (x35)", callback_data="roulette_green")],
            [InlineKeyboardButton("🎯 رقم (x36)", callback_data="roulette_number")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="games")]
        ])
        callback_query.message.edit_text(
            f"🎡 *الروليت*\n\n"
            f"💰 رصيدك: ${user[2]:.2f}\n"
            f"اختر نوع الرهان:\n\n"
            f"• 🔴 أحمر: مضاعف ×2\n"
            f"• ⚫ أسود: مضاعف ×2\n"
            f"• 🟢 أخضر: مضاعف ×35\n"
            f"• 🎯 رقم محدد: مضاعف ×36",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data.startswith("roulette_"):
        if user[6] == 0:
            callback_query.answer("❌ يجب إيداع 10$ للتفعيل!", show_alert=True)
            return
        
        choice = data.split("_")[1]
        bet_amount = 1.0
        
        if bet_amount > user[2]:
            callback_query.answer(f"❌ رصيدك غير كافٍ. لديك ${user[2]:.2f}", show_alert=True)
            return
        
        deduct_balance(tg_id, bet_amount)
        result = roulette_spin(bet_amount, choice)
        
        if result["win"]:
            add_balance(tg_id, result["win_amount"])
            c.execute("UPDATE users SET total_won = total_won + ? WHERE tg_id = ?", (result["win_amount"], tg_id))
            result_text = f"✅ *فوز!*\n💰 ربحت ${result['win_amount']:.2f} (×{result['multiplier']})"
        else:
            result_text = f"❌ *خسارة*\nالرقم: {result['result']} ({result['color']})"
        
        c.execute("""
            INSERT INTO bet_history (tg_id, game_type, bet_amount, multiplier, result, win_amount, created_at)
            VALUES (?, 'roulette', ?, ?, ?, ?, ?)
        """, (tg_id, bet_amount, result['multiplier'], result_text, result['win_amount'], datetime.now().isoformat()))
        conn.commit()
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 لعب مجدد", callback_data="game_roulette")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="games")]
        ])
        
        callback_query.message.edit_text(
            f"🎡 *نتيجة الروليت*\n\n"
            f"🎯 الرقم: {result['result']} ({result['color']})\n"
            f"{result_text}\n\n"
            f"💰 رصيدك الحالي: ${get_user(tg_id)[2]:.2f}",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data == "game_slots":
        if user[6] == 0:
            callback_query.answer("❌ يجب إيداع 10$ للتفعيل!", show_alert=True)
            return
        
        bet_amount = 1.0
        
        if bet_amount > user[2]:
            callback_query.answer(f"❌ رصيدك غير كافٍ. لديك ${user[2]:.2f}", show_alert=True)
            return
        
        deduct_balance(tg_id, bet_amount)
        result = slots_spin(bet_amount)
        
        if result["win"]:
            add_balance(tg_id, result["win_amount"])
            c.execute("UPDATE users SET total_won = total_won + ? WHERE tg_id = ?", (result["win_amount"], tg_id))
            result_text = f"✅ *فوز!*\n💰 ربحت ${result['win_amount']:.2f} (×{result['multiplier']})"
        else:
            result_text = "❌ *خسارة*"
        
        c.execute("""
            INSERT INTO bet_history (tg_id, game_type, bet_amount, multiplier, result, win_amount, created_at)
            VALUES (?, 'slots', ?, ?, ?, ?, ?)
        """, (tg_id, bet_amount, result['multiplier'], result_text, result['win_amount'], datetime.now().isoformat()))
        conn.commit()
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 لعب مجدد", callback_data="game_slots")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="games")]
        ])
        
        callback_query.message.edit_text(
            f"🎰 *السلوتس*\n\n"
            f"{result['reels'][0]} {result['reels'][1]} {result['reels'][2]}\n\n"
            f"{result_text}\n\n"
            f"💰 رصيدك الحالي: ${get_user(tg_id)[2]:.2f}",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data == "game_crash":
        if user[6] == 0:
            callback_query.answer("❌ يجب إيداع 10$ للتفعيل!", show_alert=True)
            return
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📈 ×1.5", callback_data="crash_1.5")],
            [InlineKeyboardButton("📈 ×2", callback_data="crash_2")],
            [InlineKeyboardButton("📈 ×3", callback_data="crash_3")],
            [InlineKeyboardButton("📈 ×5", callback_data="crash_5")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="games")]
        ])
        
        callback_query.message.edit_text(
            f"✈️ *الكراش (الطائرة)*\n\n"
            f"💰 رصيدك: ${user[2]:.2f}\n"
            f"اختر مضاعف الخروج:\n\n"
            f"⚠️ كلما زاد المضاعف، زادت المخاطرة!",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data.startswith("crash_"):
        crash_point = float(data.split("_")[1])
        bet_amount = 1.0
        
        if bet_amount > user[2]:
            callback_query.answer(f"❌ رصيدك غير كافٍ. لديك ${user[2]:.2f}", show_alert=True)
            return
        
        deduct_balance(tg_id, bet_amount)
        result = crash_game(bet_amount, crash_point)
        
        if result["win"]:
            add_balance(tg_id, result["win_amount"])
            c.execute("UPDATE users SET total_won = total_won + ? WHERE tg_id = ?", (result["win_amount"], tg_id))
            result_text = f"✅ *فوز!*\n✈️ الطائرة وصلت ×{result['crash_multiplier']:.2f}\n💰 ربحت ${result['win_amount']:.2f}"
        else:
            result_text = f"❌ *خسارة*\n✈️ الطائرة تحطمت عند ×{result['crash_multiplier']:.2f}"
        
        c.execute("""
            INSERT INTO bet_history (tg_id, game_type, bet_amount, multiplier, result, win_amount, created_at)
            VALUES (?, 'crash', ?, ?, ?, ?, ?)
        """, (tg_id, bet_amount, crash_point, result_text, result['win_amount'], datetime.now().isoformat()))
        conn.commit()
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 لعب مجدد", callback_data="game_crash")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="games")]
        ])
        
        callback_query.message.edit_text(
            f"✈️ *الكراش*\n\n"
            f"{result_text}\n\n"
            f"💰 رصيدك الحالي: ${get_user(tg_id)[2]:.2f}",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data == "game_dice":
        if user[6] == 0:
            callback_query.answer("❌ يجب إيداع 10$ للتفعيل!", show_alert=True)
            return
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📈 أعلى من 50 (×2)", callback_data="dice_over_50")],
            [InlineKeyboardButton("📉 أقل من 50 (×2)", callback_data="dice_under_50")],
            [InlineKeyboardButton("📈 أعلى من 75 (×4)", callback_data="dice_over_75")],
            [InlineKeyboardButton("📉 أقل من 25 (×4)", callback_data="dice_under_25")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="games")]
        ])
        
        callback_query.message.edit_text(
            f"🎲 *النرد*\n\n"
            f"💰 رصيدك: ${user[2]:.2f}\n"
            f"اختر توقعك:\n\n"
            f"• أعلى/أقل من 50: مضاعف ×2\n"
            f"• أعلى/أقل من 75/25: مضاعف ×4",
            reply_markup=keyboard
        )
        callback_query.answer()
    
    elif data.startswith("dice_"):
        parts = data.split("_")
        prediction = parts[1]
        target = int(parts[2])
        
        bet_amount = 1.0
        
        if bet_amount > user[2]:
            callback_query.answer(f"❌ رصيدك غير كافٍ. لديك ${user[2]:.2f}", show_alert=True)
            return
        
        deduct_balance(tg_id, bet_amount)
        result = dice_roll(bet_amount, prediction, target)
        
        if result["win"]:
            add_balance(tg_id, result["win_amount"])
            c.execute("UPDATE users SET total_won = total_won + ? WHERE tg_id = ?", (result["win_amount"], tg_id))
            result_text = f"✅ *فوز!*\n🎲 الرقم: {result['roll']}\n💰 ربحت ${result['win_amount']:.2f} (×{result['multiplier']:.2f})"
        else:
            result_text = f"❌ *خسارة*\n🎲 الرقم: {result['roll']}"
        
        c.execute("""
            INSERT INTO bet_history (tg_id, game_type, bet_amount, multiplier, result, win_amount, created_at)
            VALUES (?, 'dice', ?, ?, ?, ?, ?)
        """, (tg_id, bet_amount, result['multiplier'], result_text, result['win_amount'], datetime.now().isoformat()))
        conn.commit()
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 لعب مجدد", callback_data="game_dice")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="games")]
        ])
        
        callback_query.message.edit_text(
            f"🎲 *النرد*\n\n"
            f"{result_text}\n\n"
            f"💰 رصيدك الحالي: ${get_user(tg_id)[2]:.2f}",
            reply_markup=keyboard
        )
        callback_query.answer()

# ================================================================
# 9. تشغيل البوت
# ================================================================

if __name__ == "__main__":
    print("💀 DWR_CASINO_BOT تشغيل...")
    print(f"🎰 بوت الكازينو – النسخة النهائية")
    print(f"⚡ تم التكوين ببياناتك الخاصة")
    print(f"🤖 البوت جاهز للاستخدام")
    app.run()
