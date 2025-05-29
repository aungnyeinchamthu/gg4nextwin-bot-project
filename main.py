import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
ADMIN_GROUP_ID = int(os.environ.get("ADMIN_GROUP_ID", "-1001234567890"))

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            referral_by INTEGER,
            total_deposit INTEGER DEFAULT 0,
            total_withdraw INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'bronze',
            cashback_point INTEGER DEFAULT 0,
            remark TEXT,
            phone_number TEXT
        )
    """)
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or f"user_{user_id}"
    first_name = user.first_name or ""
    last_name = user.last_name or ""

    # Extract referral if exists
    referral_by = None
    if context.args:
        try:
            referral_by = int(context.args[0])
        except ValueError:
            referral_by = None

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    # Check if user already exists
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()

    if not row:
        c.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, referral_by)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, referral_by))
        conn.commit()

        # Notify admin group
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"👤 New user registered:\n"
                 f"ID: {user_id}\nUsername: @{username}\nFirst Name: {first_name}\nLast Name: {last_name}\n"
                 f"Referral: {referral_by}"
        )

    conn.close()

    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("💳 Withdraw", callback_data='withdraw')],
        [InlineKeyboardButton("🎁 My Referral Link", callback_data='referral')],
        [InlineKeyboardButton("📊 My Stats", callback_data='stats')],
        [InlineKeyboardButton("📞 Contact Admin", callback_data='contact')]
    ]
    await update.message.reply_text(
        "👋 Welcome! Please choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == "referral":
        referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
        await query.message.reply_text(f"🎁 Your referral link:\n{referral_link}")
    elif query.data == "stats":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT total_deposit, total_withdraw, rank, cashback_point FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            deposit, withdraw, rank, cashback = row
            await query.message.reply_text(
                f"📊 Your Stats:\n"
                f"Total Deposit: {deposit}\n"
                f"Total Withdraw: {withdraw}\n"
                f"Rank: {rank}\n"
                f"Cashback Points: {cashback}"
            )
        else:
            await query.message.reply_text("❌ You are not registered. Please use /start first.")
    else:
        await query.message.reply_text("⚙️ Feature under construction.")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    main()
