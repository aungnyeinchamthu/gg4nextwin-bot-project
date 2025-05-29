import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
CASHBACK_PERCENT = 0.05
REFERRAL_PERCENT = 0.0025

banks = [
    {"name": "KBZ Bank", "account_name": "GG4NextWin Co.", "account_number": "123-456-789"},
    {"name": "AYA Bank", "account_name": "GG4NextWin Co.", "account_number": "987-654-321"},
    {"name": "CB Bank", "account_name": "GG4NextWin Co.", "account_number": "555-666-777"},
]

taken_requests = {}
admin_active = {}
pending_replies = {}

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            xbet_id TEXT,
            amount INTEGER,
            bank TEXT,
            slip_file TEXT,
            points INTEGER DEFAULT 0,
            referral_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("💰 Deposit", callback_data='deposit')]]
    await update.message.reply_text("👋 Welcome! Please choose an option:",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username or f"user_{user_id}"

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
              (user_id, username))
    conn.commit()

    if query.data == 'deposit':
        c.execute("UPDATE users SET xbet_id=NULL, amount=NULL, bank=NULL, slip_file=NULL WHERE telegram_id=?", (user_id,))
        conn.commit()
        await query.message.reply_text("Please enter your 1xBet ID (9–13 digits):")
    conn.close()
    await query.answer()

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT xbet_id, amount, bank, slip_file FROM users WHERE telegram_id=?", (user_id,))
    row = c.fetchone()

    if row and not row[0]:
        if text.isdigit() and 9 <= len(text) <= 13:
            c.execute("UPDATE users SET xbet_id=? WHERE telegram_id=?", (text, user_id))
            conn.commit()
            await update.message.reply_text("✅ Enter deposit amount (minimum 1000 MMK):")
        else:
            await update.message.reply_text("❌ Invalid ID. Please enter 9–13 digit number:")
    elif row and not row[1]:
        if text.isdigit() and int(text) >= 1000:
            amount = int(text)
            c.execute("UPDATE users SET amount=? WHERE telegram_id=?", (amount, user_id))
            conn.commit()
            buttons = [[InlineKeyboardButton(bank['name'], callback_data=f"bank_{i}")] for i, bank in enumerate(banks)]
            await update.message.reply_text("🏦 Select a bank:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await update.message.reply_text("❌ Invalid amount. Please enter ≥1000 MMK:")
    conn.close()

async def bank_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bank_index = int(query.data.split("_")[1])
    selected_bank = banks[bank_index]
    user_id = query.from_user.id

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET bank=? WHERE telegram_id=?", (selected_bank['name'], user_id))
    conn.commit()
    conn.close()

    bank_info = (
        f"✅ You selected {selected_bank['name']}.\n"
        f"Account Name: {selected_bank['account_name']}\n"
        f"Account Number: {selected_bank['account_number']}\n\n"
        f"📎 Please send your payment slip."
    )
    await query.message.reply_text(bank_info)
    await query.answer()

async def slip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT xbet_id, amount, bank FROM users WHERE telegram_id=?", (user_id,))
    xbet_id, amount, bank = c.fetchone()

    file_id = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
    c.execute("UPDATE users SET slip_file=? WHERE telegram_id=?", (file_id, user_id))
    conn.commit()

    caption = (
        f"🧾 Deposit Request\n"
        f"👤 @{username}\n"
        f"🆔 1xBet ID: {xbet_id}\n"
        f"💰 Amount: {amount} MMK\n"
        f"🏦 Bank: {bank}"
    )

    sent = await context.bot.send_photo(ADMIN_GROUP_ID, file_id, caption=caption)

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Take", callback_data=f"take_{user_id}")],
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")]
    ])
    await context.bot.edit_message_reply_markup(ADMIN_GROUP_ID, sent.message_id, reply_markup=buttons)
    await update.message.reply_text("✅ Slip sent to admin for review.")
    conn.close()

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, target_id = query.data.split("_")
    target_id = int(target_id)
    admin_id = query.from_user.id
    admin_username = query.from_user.username or f"admin_{admin_id}"

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    if action == "take":
        if admin_id in admin_active:
            await query.answer("❌ You already have an active request.", show_alert=True)
            conn.close()
            return
        if target_id in taken_requests:
            await query.answer("❌ Another admin took this.", show_alert=True)
            conn.close()
            return
        taken_requests[target_id] = admin_id
        admin_active[admin_id] = target_id
        await context.bot.send_message(ADMIN_GROUP_ID, f"🛡️ @{admin_username} took request for user {target_id}.")
        await query.answer("🔒 Taken.", show_alert=True)

    elif action == "approve":
        if taken_requests.get(target_id) != admin_id:
            await query.answer("❌ You didn't take this.", show_alert=True)
            conn.close()
            return
        c.execute("UPDATE users SET points=points+10 WHERE telegram_id=?", (target_id,))
        conn.commit()
        await context.bot.send_message(target_id, "✅ Your deposit has been approved! 🎉")
        await query.message.edit_caption(query.message.caption + f"\n✅ Approved by @{admin_username}.")
        taken_requests.pop(target_id, None)
        admin_active.pop(admin_id, None)

    elif action == "reject":
        if taken_requests.get(target_id) != admin_id:
            await query.answer("❌ You didn't take this.", show_alert=True)
            conn.close()
            return
        reject_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Wrong ID", callback_data=f"reject_id_{target_id}")],
            [InlineKeyboardButton("Wrong Amount", callback_data=f"reject_amount_{target_id}")],
            [InlineKeyboardButton("Wrong Slip", callback_data=f"reject_slip_{target_id}")]
        ])
        await query.message.reply_text(f"❌ Select rejection reason for user {target_id}:",
                                       reply_markup=reject_buttons)
        taken_requests.pop(target_id, None)
        admin_active.pop(admin_id, None)
    conn.close()
    await query.answer()

async def rejection_reason_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reason, target_id = query.data.split("_")[1:]
    target_id = int(target_id)

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    if reason == "id":
        await context.bot.send_message(target_id, "❌ Wrong ID. Please re-enter your 1xBet ID:")
        c.execute("UPDATE users SET xbet_id=NULL WHERE telegram_id=?", (target_id,))
    elif reason == "amount":
        await context.bot.send_message(target_id, "❌ Wrong amount. Please re-enter your deposit amount:")
        c.execute("UPDATE users SET amount=NULL WHERE telegram_id=?", (target_id,))
    elif reason == "slip":
        await context.bot.send_message(target_id, "❌ Wrong slip. Please resend your payment slip:")
        c.execute("UPDATE users SET slip_file=NULL WHERE telegram_id=?", (target_id,))
    conn.commit()
    conn.close()
    await query.answer("Rejection reason sent to user.")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(deposit)$"))
    app.add_handler(CallbackQueryHandler(bank_selection, pattern="^bank_"))
    app.add_handler(CallbackQueryHandler(admin_handler, pattern="^(take|approve|reject)_"))
    app.add_handler(CallbackQueryHandler(rejection_reason_handler, pattern="^reject_(id|amount|slip)_"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, slip_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
