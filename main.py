import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Set in Railway environment
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))  # Set as negative int, e.g., -1001234567890

# --- Initialize database ---
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            referral_code TEXT,
            referred_by TEXT,
            total_deposit INTEGER DEFAULT 0,
            total_withdraw INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'bronze',
            cashback_points INTEGER DEFAULT 0,
            phone_number TEXT,
            recovery_code TEXT
        )
    """)
    conn.commit()
    conn.close()

# --- Generate referral code ---
def generate_referral_code(user_id):
    return f"ref{user_id}"

# --- /start handler ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    args = context.args
    referred_by = args[0] if args else None

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    existing_user = c.fetchone()

    if existing_user:
        await update.message.reply_text("👋 Welcome back! You're already registered.")
    else:
        referral_code = generate_referral_code(user_id)
        c.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, referral_code, referred_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, referral_code, referred_by))
        conn.commit()
        await update.message.reply_text("✅ You have been registered in the system!")

        if referred_by:
            await context.bot.send_message(
                ADMIN_GROUP_ID,
                f"👥 New user @{username} joined with referral {referred_by}."
            )

    # Show main menu
    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data='menu_deposit')],
        [InlineKeyboardButton("💸 Withdraw", callback_data='menu_withdraw')],
        [InlineKeyboardButton("🎁 Cashback", callback_data='menu_cashback')],
        [InlineKeyboardButton("🏆 My Rank", callback_data='menu_rank')],
        [InlineKeyboardButton("📊 My Stats", callback_data='menu_stats')],
        [InlineKeyboardButton("📞 Update Phone", callback_data='menu_phone')],
        [InlineKeyboardButton("🔗 My Referral Link", callback_data='menu_referral')]
    ]
    await update.message.reply_text("Please choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    conn.close()

# --- Button menu handler ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    if query.data == 'menu_referral':
        c.execute("SELECT referral_code FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if row:
            referral_link = f"https://t.me/{context.bot.username}?start={row[0]}"
            await query.message.reply_text(f"🔗 Your referral link:\n{referral_link}")
        else:
            await query.message.reply_text("❌ User not found.")

    elif query.data == 'menu_stats':
        c.execute("SELECT total_deposit, total_withdraw, cashback_points, rank FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if row:
            deposit, withdraw, points, rank = row
            await query.message.reply_text(
                f"📊 Your Stats:\n"
                f"💰 Total Deposit: {deposit}\n"
                f"💸 Total Withdraw: {withdraw}\n"
                f"🎁 Cashback Points: {points}\n"
                f"🏆 Rank: {rank}"
            )
        else:
            await query.message.reply_text("❌ User not found.")

    else:
        await query.message.reply_text(f"🔧 You selected: {query.data}")
    conn.close()

# --- Main function ---
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
