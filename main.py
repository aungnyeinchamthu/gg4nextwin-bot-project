import os
from telegram.ext import ApplicationBuilder, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

async def start(update, context):
    await update.message.reply_text("👋 Hello! I am your bot, ready on Railway!")

def main():
    if not BOT_TOKEN or not WEBHOOK_URL:
        raise ValueError("❌ BOT_TOKEN and WEBHOOK_URL must be set in Railway environment variables.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    main()
