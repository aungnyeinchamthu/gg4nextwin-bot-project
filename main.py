import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Config
BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID")) or -1001234567890

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
            total_deposit INTEGER DEFAULT 0,
            total_withdraw INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'Bronze',
            cashback_points INTEGER DEFAULT 0,
            phone_number TEXT,
            referral_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    referred_by = int(args[0]) if args else None
    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or ""
    last_name = user.last_name or ""

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    # Check if user already exists
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    existing_user = c.fetchone()

    if not existing_user:
        c.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, referral_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, referred_by))
        conn.commit()

        # Log to admin group
        await context.bot.send_message(
            ADMIN_GROUP_ID,
            f"🆕 New user registered:\n"
            f"👤 @{username} ({first_name} {last_name})\n"
            f"Referral: {referred_by if referred_by else 'None'}"
        )

    conn.close()

    # Show menu
    keyboard = [
        [InlineKeyboardButton("🎯 My Referral Link", callback_data='referral_link')],
        # Add other menu buttons if needed
    ]
    await update.message.reply_text(
        f"👋 Welcome, {first_name}! Please choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == 'referral_link':
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        await query.message.reply_text(f"🎯 Your referral link:\n{referral_link}")
        await context.bot.send_message(
            ADMIN_GROUP_ID,
            f"🔗 User @{query.from_user.username or user_id} generated their referral link."
        )
        await query.answer("Referral link generated!")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
