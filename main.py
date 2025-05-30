import os
import asyncio
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
RAILWAY_STATIC_URL = os.getenv("RAILWAY_STATIC_URL")
PORT = int(os.getenv("PORT", 8000))
WEBHOOK_URL = f"https://{RAILWAY_STATIC_URL}/webhook"

# Initialize database
conn = sqlite3.connect("bot.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    total_deposit INTEGER DEFAULT 0,
    total_withdraw INTEGER DEFAULT 0,
    rank TEXT DEFAULT 'bronze',
    referral_by INTEGER,
    cashback_points INTEGER DEFAULT 0,
    remark TEXT,
    phone_number TEXT
)''')
conn.commit()
conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referral_by = None

    # Check if coming from referral link
    if context.args:
        try:
            referral_by = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid referral link, continuing without referral.")

    # Insert or update user in DB
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
    if c.fetchone():
        await update.message.reply_text("👋 Welcome back!")
    else:
        c.execute('''INSERT INTO users (user_id, username, first_name, last_name, referral_by)
                     VALUES (?, ?, ?, ?, ?)''',
                  (user.id, user.username, user.first_name, user.last_name, referral_by))
        conn.commit()
        await update.message.reply_text("🎉 You have been registered!")
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"👤 New user registered:\nID: {user.id}\nUsername: @{user.username}\nReferral by: {referral_by}"
        )
    conn.close()

    # Show main menu
    keyboard = [
        [InlineKeyboardButton("Deposit", callback_data="deposit")],
        [InlineKeyboardButton("Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("Referral Link", callback_data="referral")],
        [InlineKeyboardButton("Contact", callback_data="contact")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please choose an option:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "deposit":
        await query.edit_message_text("💰 Deposit feature under construction.")
    elif query.data == "withdraw":
        await query.edit_message_text("🏧 Withdraw feature under construction.")
    elif query.data == "referral":
        referral_link = f"https://t.me/{context.bot.username}?start={user.id}"
        await query.edit_message_text(f"🔗 Your referral link:\n{referral_link}")
    elif query.data == "contact":
        await query.edit_message_text("📞 Contact us at: support@example.com")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    asyncio.run(main())
