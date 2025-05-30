import os
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SECRET_TOKEN = os.getenv("SECRET_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))

async def start(update, context):
    await update.message.reply_text("Hello! Welcome to the bot.")

async def help_command(update, context):
    await update.message.reply_text("This is the help message.")

async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    await application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        webhook_url=WEBHOOK_URL,
        secret_token=SECRET_TOKEN,
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
