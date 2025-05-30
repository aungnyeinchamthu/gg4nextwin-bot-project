import os
import asyncio
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL").replace('"', '')  # remove any extra quotes
SECRET_TOKEN = os.getenv("SECRET_TOKEN")
PORT = int(os.getenv("PORT", 8000))

async def start(update, context):
    await update.message.reply_text("🤖 Hello! I am GG4NEXTWIN Bot, ready to serve you!")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    await app.initialize()
    await app.start()

    # Set webhook
    await app.bot.set_webhook(
        url=f"https://{WEBHOOK_URL}",
        secret_token=SECRET_TOKEN
    )

    print(f"✅ Webhook set at https://{WEBHOOK_URL}")

    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
    )

    await app.updater.idle()

    await app.stop()
    await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
