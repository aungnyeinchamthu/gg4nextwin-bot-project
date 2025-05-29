import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID")) or -1001234567890  # example

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            total_deposit INTEGER DEFAULT 0,
            total_withdraw INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'bronze',
            cashback_points INTEGER DEFAULT 0,
            referral_id INTEGER,
            remark TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name

    inviter_id = int(args[0]) if args else None

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    exists = c.fetchone()
    if not exists:
        c.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, referral_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, inviter_id))
        conn.commit()

        # Log in admin group
        await context.bot.send_message(
            ADMIN_GROUP_ID,
            f"👤 New user registered!\nID: {user_id}\nUsername: @{username}\nReferral: {inviter_id}"
        )
    conn.close()

    # Show main menu
    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("🎯 My Referral Link", callback_data="get_referral")]
    ]
    await update.message.reply_text("👋 Welcome! Please choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "get_referral":
        referral_link = f"https://t.me/{context.bot.username}?start={user.id}"
        await query.message.reply_text(f"🎯 Your referral link:\n{referral_link}")

    elif query.data == "deposit":
        await query.message.reply_text("💬 Please enter the amount you want to deposit (this demo stops here).")

async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ I didn't understand that. Please use /start.")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_handler))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
