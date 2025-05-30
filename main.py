import os
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env vars
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

if not BOT_TOKEN or not ADMIN_GROUP_ID or not WEBHOOK_URL or not SECRET_TOKEN:
    raise ValueError("Missing required environment variables.")

# Database setup
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
            rank TEXT DEFAULT 'Bronze',
            cashback_point INTEGER DEFAULT 0,
            remark TEXT,
            phone TEXT
        )
    """)
    conn.commit()
    conn.close()

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name
    referral_by = None

    if context.args:
        try:
            referral_by = int(context.args[0])
        except (IndexError, ValueError):
            await update.message.reply_text("Invalid referral ID. Proceeding without referral.")

    try:
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if c.fetchone():
            await update.message.reply_text("👋 Welcome back!")
        else:
            c.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, referral_by)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, first_name, last_name, referral_by))
            conn.commit()
            await update.message.reply_text("✅ Registered successfully!")
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"👤 New user registered:\nID: {user_id}\nUsername: @{username}\nReferral by: {referral_by}"
            )
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        await update.message.reply_text("Database error occurred.")
    finally:
        conn.close()

    # Show main menu
    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("💸 Withdraw", callback_data='withdraw')],
        [InlineKeyboardButton("🎯 Referral", callback_data='referral')],
        [InlineKeyboardButton("📞 Contact", callback_data='contact')]
    ]
    await update.message.reply_text("Please choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

# Button handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'deposit':
        await query.message.reply_text("💰 Deposit feature is under construction.")
    elif data == 'withdraw':
        await query.message.reply_text("💸 Withdraw feature is under construction.")
    elif data == 'referral':
        ref_link = f"https://t.me/{context.bot.username}?start={query.from_user.id}"
        await query.message.reply_text(f"🎯 Your referral link:\n{ref_link}")
    elif data == 'contact':
        await query.message.reply_text("📞 Contact support at @youradmin.")

def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🤖 Bot is running (webhook mode)...")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        webhook_url=WEBHOOK_URL,
        secret_token=SECRET_TOKEN
    )

if __name__ == "__main__":
    main()
