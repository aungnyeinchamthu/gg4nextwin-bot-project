import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
import asyncio

# Load env variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SECRET_TOKEN = os.getenv("SECRET_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Simple /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("💸 Withdraw", callback_data='withdraw')],
        [InlineKeyboardButton("📣 Referral", callback_data='referral')],
        [InlineKeyboardButton("📞 Contact", callback_data='contact')]
    ]
    await update.message.reply_text(
        f"👋 Hello {user.first_name}! Welcome to GG4NextWin Bot. Choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    # Notify admin
    try:
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"🆕 User started bot: @{user.username} ({user.id})"
        )
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")

# Simple button handler (expandable)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'deposit':
        await query.message.reply_text("💰 Deposit feature coming soon!")
    elif query.data == 'withdraw':
        await query.message.reply_text("💸 Withdraw feature coming soon!")
    elif query.data == 'referral':
        user = query.from_user
        ref_link = f"https://t.me/{context.bot.username}?start={user.id}"
        await query.message.reply_text(f"📣 Your referral link:\n{ref_link}")
    elif query.data == 'contact':
        await query.message.reply_text("📞 Contact us at support@example.com")

# Main runner
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Run webhook
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        webhook_url=WEBHOOK_URL,
        secret_token=SECRET_TOKEN,
    )

if __name__ == "__main__":
    asyncio.run(main())
