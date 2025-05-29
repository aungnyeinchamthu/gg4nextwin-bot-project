import os
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command, StateFilter

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

if not BOT_TOKEN or not ADMIN_GROUP_ID:
    raise ValueError("BOT_TOKEN and ADMIN_GROUP_ID must be set in environment variables")

ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class DepositStates(StatesGroup):
    awaiting_xbet_id = State()
    awaiting_amount = State()
    awaiting_bank = State()
    awaiting_slip = State()
    resubmit_field = State()

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
                original_id INTEGER DEFAULT NULL
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
        await message.answer("❌ Invalid ID. Please enter a 9–13 digit number:")
        return
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("INSERT INTO requests (user_id, username, xbet_id) VALUES (?, ?, ?)",
                         (message.from_user.id, message.from_user.username or f"user_{message.from_user.id}", xbet_id))
        await db.commit()
    await state.set_state(DepositStates.awaiting_amount)
    await message.answer("✅ Please enter the amount (min 1000 MMK):")

@dp.message(StateFilter(DepositStates.awaiting_amount))
async def handle_amount(message: types.Message, state: FSMContext):
    amount = message.text.strip()
    if not (amount.isdigit() and int(amount) >= 1000):
        await message.answer("❌ Invalid amount. Enter number ≥ 1000:")
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
    await message.answer("🏦 Choose a bank:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith('bank_'), StateFilter(DepositStates.awaiting_bank))
async def handle_bank(callback: types.CallbackQuery, state: FSMContext):
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
    caption = f"🧾 Request #{req[0]}\n👤 @{message.from_user.username}\n🆔 {req[1]}\n💰 {req[2]}\n🏦 {req[3]}"
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🔒 Take", callback_data=f"take_{req[0]}")],
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{req[0]}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{req[0]}")]
    ])
    await bot.send_photo(ADMIN_GROUP_ID, file_id, caption=caption, reply_markup=buttons)
    await message.answer("✅ Slip sent for admin review.")
    await state.clear()

@dp.callback_query(F.data.startswith(('take_', 'approve_', 'reject_')))
async def handle_admin_actions(callback: types.CallbackQuery):
    action, req_id = callback.data.split("_")
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT user_id FROM requests WHERE id=?", (req_id,))
        row = await cur.fetchone()
        if not row:
            await callback.answer("❌ Request not found.", show_alert=True)
            return
        user_id = row[0]

        if action == "take":
            await callback.answer("Taken.")
            await callback.message.answer(f"🔒 {callback.from_user.username} is handling this request.")

        elif action == "approve":
            await db.execute("UPDATE requests SET status='approved' WHERE id=?", (req_id,))
            await db.commit()
            await bot.send_message(user_id, "✅ Your deposit has been approved! 🎉")
            await callback.answer("Approved.")

        elif action == "reject":
            reject_buttons = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("Wrong ID", callback_data=f"reject_reason_id_{req_id}")],
                [InlineKeyboardButton("Wrong Amount", callback_data=f"reject_reason_amount_{req_id}")],
                [InlineKeyboardButton("Wrong Slip", callback_data=f"reject_reason_slip_{req_id}")]
            ])
            await callback.message.answer("❌ Select rejection reason:", reply_markup=reject_buttons)
            await callback.answer("Rejection reason requested.")

@dp.callback_query(F.data.startswith('reject_reason_'))
async def handle_reject_reason(callback: types.CallbackQuery):
    _, reason, req_id = callback.data.split("_", 2)
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT user_id, xbet_id, amount, bank FROM requests WHERE id=?", (req_id,))
        row = await cur.fetchone()
        if not row:
            await callback.answer("❌ Request not found.", show_alert=True)
            return
        user_id, xbet_id, amount, bank = row

        # Clone data into a new pending request
        await db.execute("""
            INSERT INTO requests (user_id, username, xbet_id, amount, bank, status, original_id)
            SELECT user_id, username, ?, ?, ?, 'pending', id FROM requests WHERE id=?
        """, (
            None if reason == 'id' else xbet_id,
            None if reason == 'amount' else amount,
            None if reason == 'slip' else bank,
            req_id
        ))
        await db.commit()

    # Ask only for the rejected part
    if reason == 'id':
        await bot.send_message(user_id, "❌ Your ID was wrong. Please enter your correct 1xBet ID:")
    elif reason == 'amount':
        await bot.send_message(user_id, "❌ Your amount was wrong. Please enter the correct amount:")
    elif reason == 'slip':
        await bot.send_message(user_id, "❌ Your slip was wrong. Please resend your deposit slip:")
    await callback.answer("User notified.")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
