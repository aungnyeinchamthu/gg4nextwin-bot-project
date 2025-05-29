import os
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class DepositStates(StatesGroup):
    awaiting_xbet_id = State()
    awaiting_amount = State()
    awaiting_bank = State()
    awaiting_slip = State()

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
            status TEXT DEFAULT 'pending'
        )
        """)
        await db.commit()

@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Deposit", callback_data='deposit')]
    ])
    await message.answer("👋 Welcome! Please choose an option:", reply_markup=keyboard)
    await state.clear()

@dp.callback_query(F.data == 'deposit')
async def deposit_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(DepositStates.awaiting_xbet_id)
    await callback.message.answer("Please enter your 1xBet ID (9–13 digits):")
    await callback.answer()

@dp.message(StateFilter(DepositStates.awaiting_xbet_id))
async def handle_xbet_id(message: types.Message, state: FSMContext):
    xbet_id = message.text.strip()
    if not (xbet_id.isdigit() and 9 <= len(xbet_id) <= 13):
        await message.answer("❌ Invalid ID format. Please enter a 9–13 digit number:")
        return
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("INSERT INTO requests (user_id, username, xbet_id) VALUES (?, ?, ?)",
                         (message.from_user.id, message.from_user.username or f"user_{message.from_user.id}", xbet_id))
        await db.commit()
    await state.set_state(DepositStates.awaiting_amount)
    await message.answer("✅ Please enter the amount you want to deposit (min 1000 MMK):")

@dp.message(StateFilter(DepositStates.awaiting_amount))
async def handle_amount(message: types.Message, state: FSMContext):
    amount = message.text.strip()
    if not (amount.isdigit() and int(amount) >= 1000):
        await message.answer("❌ Invalid amount. Please enter a number ≥ 1000:")
        return
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("UPDATE requests SET amount=? WHERE user_id=? AND status='pending'",
                         (int(amount), message.from_user.id))
        await db.commit()
    await state.set_state(DepositStates.awaiting_bank)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="KBZ Bank", callback_data='bank_KBZ')],
        [InlineKeyboardButton(text="AYA Bank", callback_data='bank_AYA')],
        [InlineKeyboardButton(text="CB Bank", callback_data='bank_CB')],
    ])
    await message.answer("🏦 Please choose a bank:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith('bank_'), StateFilter(DepositStates.awaiting_bank))
async def handle_bank_selection(callback: types.CallbackQuery, state: FSMContext):
    bank_name = callback.data.split("_")[1]
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("UPDATE requests SET bank=? WHERE user_id=? AND status='pending'",
                         (bank_name, callback.from_user.id))
        await db.commit()
    await state.set_state(DepositStates.awaiting_slip)
    await callback.message.answer("📎 Please send your deposit slip (photo or document).")
    await callback.answer()

@dp.message(F.content_type.in_(['photo', 'document']), StateFilter(DepositStates.awaiting_slip))
async def handle_slip(message: types.Message, state: FSMContext):
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
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 Take", callback_data=f"take_{req[0]}")],
        [InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{req[0]}")],
        [InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{req[0]}")]
    ])
    await bot.send_photo(ADMIN_GROUP_ID, file_id, caption=caption, reply_markup=buttons)
    await message.answer("✅ Your slip has been sent for admin review.")
    await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
