import os
from telegram.ext import ApplicationBuilder, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update, context):
    await update.message.reply_text("Hello, I am your bot!")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    if os.getenv("RAILWAY_ENVIRONMENT"):
        # On Railway, use webhook
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get('PORT', 8443)),
            webhook_url=f"https://{os.environ['RAILWAY_STATIC_URL']}/{BOT_TOKEN}"
        )
    else:
        # Local: use polling
        app.run_polling()

if __name__ == "__main__":
    main()
