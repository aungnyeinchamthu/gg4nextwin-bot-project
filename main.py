import os
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('RAILWAY_STATIC_URL') + '/webhook'  # e.g., https://your-app.up.railway.app/webhook
ADMIN_GROUP_ID = os.getenv('ADMIN_GROUP_ID')

if not BOT_TOKEN or not WEBHOOK_URL or not ADMIN_GROUP_ID:
    raise ValueError("Missing BOT_TOKEN, RAILWAY_STATIC_URL, or ADMIN_GROUP_ID environment variable!")

# Handlers
def start(update, context):
    user = update.effective_user
    buttons = [[
        InlineKeyboardButton("Deposit", callback_data='deposit'),
        InlineKeyboardButton("Withdraw", callback_data='withdraw')
    ], [
        InlineKeyboardButton("Referral", callback_data='referral'),
        InlineKeyboardButton("Contact", callback_data='contact')
    ]]
    markup = InlineKeyboardMarkup(buttons)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Welcome {user.first_name}! Please choose an option:",
        reply_markup=markup
    )

def button_handler(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'deposit':
        query.edit_message_text("Deposit feature under construction.")
    elif query.data == 'withdraw':
        query.edit_message_text("Withdraw feature under construction.")
    elif query.data == 'referral':
        user_id = query.from_user.id
        referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
        query.edit_message_text(f"Your referral link: {referral_link}")
    elif query.data == 'contact':
        query.edit_message_text("Contact us at: support@example.com")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info(f"Starting bot with webhook at {WEBHOOK_URL}")

    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv('PORT', 8000)),
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
