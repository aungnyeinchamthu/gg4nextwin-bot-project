import os
from telegram.ext import Application, CommandHandler
from handlers import start, help_command

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

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
