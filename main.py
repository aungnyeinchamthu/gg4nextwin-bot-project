import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID") or -1001234567890)  # Replace with real group ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Initialize DB
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone_number TEXT,
            total_deposit INTEGER DEFAULT 0,
            total_withdraw INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'bronze',
            cashback_point INTEGER DEFAULT 0,
            referral INTEGER,
            remark TEXT
        )
    """)
    conn.commit()
    conn.close()

@dp.message(Command("start"))
async def handle_start(message: types.Message):
    referrer_id = None
    if message.text.strip() != "/start":
        parts = message.text.split()
        if len(parts) > 1 and parts[1].isdigit():
            referrer_id = int(parts[1])

    chat_id = message.from_user.id
    username = message.from_user.username or f"user_{chat_id}"
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT chat_id FROM users WHERE chat_id=?", (chat_id,))
    if c.fetchone():
        await message.answer("👋 Welcome back! You're already registered.")
    else:
        c.execute("""
            INSERT INTO users (chat_id, username, first_name, last_name, referral)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, username, first_name, last_name, referrer_id))
        conn.commit()
        await message.answer("✅ You have been registered successfully!")
        if referrer_id:
            await message.answer(f"🎉 You were referred by user ID: {referrer_id}")

    # Fetch and forward user info to admin group
    c.execute("SELECT * FROM users WHERE chat_id=?", (chat_id,))
    user_data = c.fetchone()
    conn.close()

    log_message = (
        f"📝 New User Registered / Started\n"
        f"ID: {user_data[0]}\n"
        f"Username: {user_data[1]}\n"
        f"First Name: {user_data[2]}\n"
        f"Last Name: {user_data[3]}\n"
        f"Phone: {user_data[4] or 'N/A'}\n"
        f"Total Deposit: {user_data[5]}\n"
        f"Total Withdraw: {user_data[6]}\n"
        f"Rank: {user_data[7]}\n"
        f"Cashback Points: {user_data[8]}\n"
        f"Referral: {user_data[9] or 'None'}\n"
        f"Remark: {user_data[10] or 'None'}"
    )

    try:
        await bot.send_message(ADMIN_GROUP_ID, log_message)
    except Exception as e:
        await message.answer("⚠️ Failed to log to admin group. Check permissions or group ID.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
