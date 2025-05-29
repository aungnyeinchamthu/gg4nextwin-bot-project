import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))

# Initialize database
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            referral_code TEXT,
            referred_by TEXT,
            total_deposit INTEGER DEFAULT 0,
            total_withdraw INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'bronze',
            cashback_points INTEGER DEFAULT 0,
            remark TEXT,
            phone_number TEXT
        )
    """)
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_user.id
    username = update.effective_user.username or ""
    first_name = update.effective_user.first_name or ""
    last_name = update.effective_user.last_name or ""

    # Check for referral deep link
    referrer = None
    if context.args:
        referrer = context.args[0]

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    user = c.fetchone()

    if not user:
        c.execute("INSERT INTO users (chat_id, username, first_name, last_name, referred_by) VALUES (?, ?, ?, ?, ?)",
                  (chat_id, username, first_name, last_name, referrer))
        conn.commit()
        await context.bot.send_message(ADMIN_GROUP_ID, f"👤 New user registered: @{username} (ref: {referrer})")
    conn.close()

    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("🎁 My Referral", callback_data='my_referral')],
        [InlineKeyboardButton("📊 My Stats", callback_data='my_stats')]
    ]
    await update.message.reply_text("👋 Welcome! Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def my_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    referral_link = f"https://t.me/{context.bot.username}?start={chat_id}"
    await query.message.reply_text(f"🔗 Your referral link:\n{referral_link}")

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT total_deposit, total_withdraw, rank, cashback_points FROM users WHERE chat_id = ?", (chat_id,))
    row = c.fetchone()
    conn.close()

    if row:
        deposit, withdraw, rank, cashback = row
        await query.message.reply_text(
            f"💼 Your Stats:\nDeposit: {deposit}\nWithdraw: {withdraw}\nRank: {rank}\nCashback Points: {cashback}")
    else:
        await query.message.reply_text("❌ You are not registered.")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(my_referral, pattern='^my_referral$'))
    app.add_handler(CallbackQueryHandler(my_stats, pattern='^my_stats$'))

    app.run_polling()

if __name__ == "__main__":
    main()
