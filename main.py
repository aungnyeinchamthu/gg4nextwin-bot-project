import os
import asyncio
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.environ.get("ADMIN_GROUP_ID"))
RAILWAY_STATIC_URL = os.environ.get("RAILWAY_STATIC_URL")
DATABASE = "bot.db"

# Ensure DB setup
def init_db():
    conn = sqlite3.connect(DATABASE)
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
        cashback_point INTEGER DEFAULT 0,
        remark TEXT,
        phone_number TEXT
    )''')
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
            await update.message.reply_text("Invalid referral code. Proceeding without referral.")

    # Check if user exists
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    result = c.fetchone()
    if not result:
        c.execute("INSERT INTO users (user_id, username, first_name, last_name, referral_by) VALUES (?, ?, ?, ?, ?)",
                  (user.id, user.username, user.first_name, user.last_name, referral_by))
        conn.commit()
        try:
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"👤 New user registered: @{user.username or 'N/A'} ({user.id}) referred by {referral_by or 'None'}"
            )
        except Exception as e:
            logger.error(f"Failed to send admin log: {e}")
        await update.message.reply_text("Welcome! You are registered.")
    else:
        await update.message.reply_text("Welcome back! You are already registered.")
    conn.close()

    # Send menu
    buttons = [
        [InlineKeyboardButton("💸 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("🏧 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🎁 Referral", callback_data="referral")],
        [InlineKeyboardButton("📞 Contact Support", callback_data="contact")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)

# Button handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "deposit":
        await query.edit_message_text("Deposit feature under construction.")
    elif query.data == "withdraw":
        await query.edit_message_text("Withdraw feature under construction.")
    elif query.data == "referral":
        referral_link = f"https://t.me/{context.bot.username}?start={query.from_user.id}"
        await query.edit_message_text(f"Your referral link: {referral_link}")
    elif query.data == "contact":
        await query.edit_message_text("Please contact support at @YourSupportUsername")

async def main():
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    webhook_url = f"{RAILWAY_STATIC_URL}/webhook/{BOT_TOKEN}"

    await app.bot.set_webhook(url=webhook_url, max_connections=40)

    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        webhook_path=f"/webhook/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
