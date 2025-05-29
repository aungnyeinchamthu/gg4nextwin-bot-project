import os
import aiosqlite
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            xbet_id TEXT,
            amount INTEGER,
            bank TEXT,
            slip_file TEXT,
            status TEXT DEFAULT 'pending',
            resubmitted INTEGER DEFAULT 0
        )
        """)
        await db.commit()

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("💰 Deposit", callback_data='deposit')
    )
    await message.reply("👋 Welcome! Please choose an option:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'deposit')
async def deposit_start(query: types.CallbackQuery):
    await query.message.answer("Please enter your 1xBet ID (9–13 digits):")
    await dp.current_state(user=query.from_user.id).set_state("awaiting_xbet_id")

@dp.message_handler(state="awaiting_xbet_id")
async def handle_xbet_id(message: types.Message, state):
    xbet_id = message.text.strip()
    if not (xbet_id.isdigit() and 9 <= len(xbet_id) <= 13):
        await message.reply("❌ Invalid ID format. Please enter a 9–13 digit number:")
        return
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("INSERT INTO requests (user_id, username, xbet_id) VALUES (?, ?, ?)",
                         (message.from_user.id, message.from_user.username or f"user_{message.from_user.id}", xbet_id))
        await db.commit()
    await message.reply("✅ Please enter the amount you want to deposit (min 1000 MMK):")
    await dp.current_state(user=message.from_user.id).set_state("awaiting_amount")

@dp.message_handler(state="awaiting_amount")
async def handle_amount(message: types.Message, state):
    amount = message.text.strip()
    if not (amount.isdigit() and int(amount) >= 1000):
        await message.reply("❌ Invalid amount. Please enter a number ≥ 1000:")
        return
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("UPDATE requests SET amount=? WHERE user_id=? AND status='pending'",
                         (int(amount), message.from_user.id))
        await db.commit()
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("KBZ Bank", callback_data='bank_KBZ'),
        InlineKeyboardButton("AYA Bank", callback_data='bank_AYA'),
        InlineKeyboardButton("CB Bank", callback_data='bank_CB')
    )
    await message.reply("🏦 Please choose a bank:", reply_markup=keyboard)
    await dp.current_state(user=message.from_user.id).set_state("awaiting_bank")

@dp.callback_query_handler(lambda c: c.data.startswith('bank_'), state="awaiting_bank")
async def handle_bank_selection(query: types.CallbackQuery, state):
    bank_name = query.data.split("_")[1]
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("UPDATE requests SET bank=? WHERE user_id=? AND status='pending'",
                         (bank_name, query.from_user.id))
        await db.commit()
    await query.message.answer("📎 Please send your deposit slip (photo or document).")
    await dp.current_state(user=query.from_user.id).set_state("awaiting_slip")

@dp.message_handler(content_types=types.ContentType.ANY, state="awaiting_slip")
async def handle_slip(message: types.Message, state):
    if not (message.photo or message.document):
        await message.reply("❌ Please send a valid photo or document of your slip.")
        return
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("UPDATE requests SET slip_file=? WHERE user_id=? AND status='pending'",
                         (file_id, message.from_user.id))
        await db.commit()
        cur = await db.execute("SELECT id, xbet_id, amount, bank FROM requests WHERE user_id=? AND status='pending'",
                               (message.from_user.id,))
        req = await cur.fetchone()
    caption = (f"🧾 Request #{req[0]}\n👤 User: @{message.from_user.username}\n🆔 1xBet ID: {req[1]}\n"
               f"💰 Amount: {req[2]}\n🏦 Bank: {req[3]}")
    buttons = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔒 Take", callback_data=f"take_{req[0]}"),
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{req[0]}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{req[0]}")
    )
    await bot.send_photo(ADMIN_GROUP_ID, file_id, caption=caption, reply_markup=buttons)
    await message.reply("✅ Your slip has been sent for admin review.")
    await dp.current_state(user=message.from_user.id).finish()

async def on_startup(dp):
    await init_db()
    print("🤖 Bot started...")

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, on_startup=on_startup)
