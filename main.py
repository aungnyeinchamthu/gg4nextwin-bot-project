import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, filters, MessageHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID") or -1001234567890)

# Initialize database
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
            rank TEXT DEFAULT 'bronze',
            referral_count INTEGER DEFAULT 0,
            referred_by INTEGER,
            cashback_points INTEGER DEFAULT 0,
            phone_number TEXT
        )
    """)
    conn.commit()
    conn.close()

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referred_by = None

    if args and args[0].startswith("ref"):
        referred_by = int(args[0][3:])
        await context.bot.send_message(
            ADMIN_GROUP_ID,
            f"👥 User {user.id} joined via referral from {referred_by}"
        )

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    existing = c.fetchone()

    if not existing:
        c.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, referred_by)
            VALUES (?, ?, ?, ?, ?)
        """, (user.id, user.username, user.first_name, user.last_name, referred_by))
        conn.commit()
        await update.message.reply_text("✅ You have been registered!")
    else:
        await update.message.reply_text("👋 Welcome back!")

    # Show main menu
    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("📢 Referral", callback_data="referral")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    await update.message.reply_text("Here’s the main menu:",
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    conn.close()

# Referral button handler
async def referral_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    referral_link = f"https://t.me/{context.bot.username}?start=ref{user_id}"
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        f"✅ Here’s your referral link:\n{referral_link}\nShare it to earn rewards!"
    )

# Deposit button handler (placeholder)
async def deposit_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("💰 Deposit process coming soon!")

# Help button handler (placeholder)
async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("ℹ️ Help section coming soon!")

# Handle unknown messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Unknown command. Use /start to see the menu.")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deposit_button, pattern="^deposit$"))
    app.add_handler(CallbackQueryHandler(referral_button, pattern="^referral$"))
    app.add_handler(CallbackQueryHandler(help_button, pattern="^help$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
