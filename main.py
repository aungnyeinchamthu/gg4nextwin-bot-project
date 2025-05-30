import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

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
            referral_by INTEGER,
            total_deposit INTEGER DEFAULT 0,
            total_withdraw INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'bronze',
            cashback_points INTEGER DEFAULT 0,
            phone_number TEXT
        )
    """)
    conn.commit()
    conn.close()

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referral_by = None
    if context.args:
        try:
            referral_by = int(context.args[0])
        except (IndexError, ValueError):
            await update.message.reply_text("Invalid referral code, continuing without referral.")

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
    existing_user = c.fetchone()
    if not existing_user:
        c.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, referral_by)
            VALUES (?, ?, ?, ?, ?)
        """, (user.id, user.username, user.first_name, user.last_name, referral_by))
        conn.commit()
        await update.message.reply_text("🎉 You are now registered in the system!")

        # Notify admin
        try:
            await context.bot.send_message(
                ADMIN_GROUP_ID,
                f"👤 New user registered:\n"
                f"ID: {user.id}\n"
                f"Username: @{user.username}\n"
                f"Referral: {referral_by if referral_by else 'None'}"
            )
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
    else:
        await update.message.reply_text("✅ You are already registered!")

    conn.close()

    # Show menu
    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("💸 Withdraw", callback_data='withdraw')],
        [InlineKeyboardButton("📱 Contact", callback_data='contact')],
        [InlineKeyboardButton("🎯 Referral Link", callback_data='referral')]
    ]
    await update.message.reply_text("Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

# Button callback handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'deposit':
        await query.message.reply_text("💰 Deposit feature under construction.")
    elif query.data == 'withdraw':
        await query.message.reply_text("💸 Withdraw feature under construction.")
    elif query.data == 'contact':
        await query.message.reply_text("📱 Contact us at @YourSupportUsername.")
    elif query.data == 'referral':
        referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
        await query.message.reply_text(f"🎯 Your referral link:\n{referral_link}")

# Message handler (future use)
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please use the menu buttons.")

# Main function
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Run with webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    main()

