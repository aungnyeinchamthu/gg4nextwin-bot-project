import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID") or -1001234567890)
BOT_USERNAME = os.getenv("BOT_USERNAME") or "YourBotUsername"

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
            referrer_chat_id INTEGER,
            referral_count INTEGER DEFAULT 0,
            total_deposit INTEGER DEFAULT 0,
            total_withdraw INTEGER DEFAULT 0,
            cashback_points INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'bronze'
        )
    """)
    conn.commit()
    conn.close()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_user.id
    username = update.effective_user.username or f"user_{chat_id}"
    first_name = update.effective_user.first_name or ""
    last_name = update.effective_user.last_name or ""
    args = context.args

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    user = c.fetchone()

    if not user:
        # Check referral
        referrer_id = None
        if args and args[0].startswith("ref"):
            referrer_id = int(args[0][3:])
            c.execute("UPDATE users SET referral_count = referral_count + 1 WHERE chat_id = ?", (referrer_id,))
            await context.bot.send_message(
                ADMIN_GROUP_ID,
                f"👤 @{username} ({chat_id}) joined via referral!\n🎉 Referrer: {referrer_id}"
            )

        # Insert new user
        c.execute("""
            INSERT INTO users (chat_id, username, first_name, last_name, referrer_chat_id)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, username, first_name, last_name, referrer_id))
        conn.commit()
        await update.message.reply_text("✅ You have been registered in our system!")
    else:
        await update.message.reply_text("👋 Welcome back! You’re already registered.")

    # Show menu
    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data="menu_deposit")],
        [InlineKeyboardButton("🏧 Withdraw", callback_data="menu_withdraw")],
        [InlineKeyboardButton("🎁 Cashback", callback_data="menu_cashback")],
        [InlineKeyboardButton("📊 My Stats", callback_data="menu_stats")],
        [InlineKeyboardButton("👑 My Rank", callback_data="menu_rank")],
        [InlineKeyboardButton("🔗 Referral", callback_data="menu_referral")],
        [InlineKeyboardButton("📞 Contact Support", callback_data="menu_support")]
    ]
    await update.message.reply_text("Please choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))
    conn.close()

# /referral command
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_user.id
    username = update.effective_user.username or f"user_{chat_id}"
    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref{chat_id}"
    await update.message.reply_text(
        f"🔗 Your referral link:\n{referral_link}\n\nShare this with your friends!"
    )

# Button handler (placeholder)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "menu_referral":
        await referral(update, context)
    else:
        await query.message.reply_text(f"You clicked: {query.data}")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("referral", referral))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
