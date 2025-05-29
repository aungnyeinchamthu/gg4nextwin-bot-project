import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))

# Initialize database
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            xbet_id TEXT,
            amount INTEGER,
            points INTEGER DEFAULT 0,
            step TEXT DEFAULT 'menu'
        )
    """)
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("📈 My Points", callback_data='points')],
        [InlineKeyboardButton("🎁 Cashback", callback_data='cashback')],
        [InlineKeyboardButton("👥 Referral", callback_data='referral')],
        [InlineKeyboardButton("🏦 Bank Info", callback_data='bank')],
        [InlineKeyboardButton("📞 Help", callback_data='help')],
        [InlineKeyboardButton("⚙️ Settings", callback_data='settings')],
    ]
    await update.message.reply_text(
        "👋 Welcome! Please choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)", (user_id, query.from_user.username))
    conn.commit()

    if query.data == 'deposit':
        c.execute("UPDATE users SET step='awaiting_xbet_id' WHERE telegram_id=?", (user_id,))
        conn.commit()
        await query.message.reply_text("Please enter your 1xBet ID:")
    elif query.data == 'points':
        c.execute("SELECT points FROM users WHERE telegram_id=?", (user_id,))
        points = c.fetchone()[0]
        await query.message.reply_text(f"⭐ You have {points} points.")
    elif query.data == 'cashback':
        await query.message.reply_text("💸 Cashback info coming soon!")
    elif query.data == 'referral':
        await query.message.reply_text("🔗 Referral program coming soon!")
    elif query.data == 'bank':
        await query.message.reply_text("🏦 Our banks: KBZ, AYA, CB.")
    elif query.data == 'help':
        await query.message.reply_text("📞 Contact support for help.")
    elif query.data == 'settings':
        await query.message.reply_text("⚙️ Settings coming soon!")
    conn.close()

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT step FROM users WHERE telegram_id=?", (user_id,))
    row = c.fetchone()

    if not row:
        await update.message.reply_text("Please click /start first.")
        conn.close()
        return

    step = row[0]

    if step == 'awaiting_xbet_id':
        if text.isdigit():
            c.execute("UPDATE users SET xbet_id=?, step='awaiting_amount' WHERE telegram_id=?", (text, user_id))
            conn.commit()
            await update.message.reply_text("✅ Enter deposit amount (MMK):")
        else:
            await update.message.reply_text("❌ Invalid 1xBet ID. Enter again:")
    elif step == 'awaiting_amount':
        if text.isdigit() and int(text) >= 1000:
            amount = int(text)
            points = amount // 1000
            c.execute("UPDATE users SET amount=?, points=points+?, step='menu' WHERE telegram_id=?", (amount, points, user_id))
            conn.commit()

            c.execute("SELECT username, xbet_id FROM users WHERE telegram_id=?", (user_id,))
            username, xbet_id = c.fetchone()
            caption = (
                f"🧾 New Deposit Request\n"
                f"👤 @{username or 'no_username'}\n"
                f"🆔 1xBet ID: {xbet_id}\n"
                f"💰 Amount: {amount} MMK\n"
                f"💎 Points Earned: {points}"
            )
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=caption)
            await update.message.reply_text("✅ Sent to admin for approval.")
        else:
            await update.message.reply_text("❌ Invalid amount. Enter again:")
    conn.close()

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
