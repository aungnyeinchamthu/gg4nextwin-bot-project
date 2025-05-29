import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram import F

BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Deposit", callback_data="menu_deposit")],
            [InlineKeyboardButton(text="💸 Withdraw", callback_data="menu_withdraw")],
            [InlineKeyboardButton(text="🏦 Bank Info", callback_data="menu_bankinfo")],
            [InlineKeyboardButton(text="🎁 Check Points", callback_data="menu_points")],
            [InlineKeyboardButton(text="🔗 Referral", callback_data="menu_referral")],
            [InlineKeyboardButton(text="🛟 Help", callback_data="menu_help")],
            [InlineKeyboardButton(text="⚙️ Settings", callback_data="menu_settings")]
        ]
    )
    await message.answer("👋 Welcome! Please choose an option:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("menu_"))
async def menu_handler(callback: types.CallbackQuery):
    await callback.answer(f"You selected: {callback.data}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
