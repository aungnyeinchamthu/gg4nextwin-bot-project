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

banks = ["KBZ Bank", "AYA Bank", "CB Bank"]

# Database setup
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            xbet_id TEXT,
            points INTEGER DEFAULT 0,
            referral_id INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            amount INTEGER,
            bank TEXT,
            status TEXT,
            slip TEXT
        )
    """)
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("📈 My Points", callback_data='points')],
        [InlineKeyboardButton("👥 Referral", callback_data='referral')]
    ]
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
        c.execute("UPDATE users SET xbet_id=NULL WHERE telegram_id=?", (user_id,))
        conn.commit()
        await query.message.reply_text("Please enter your 1xBet ID (9–13 digits):")
    elif query.data == 'points':
        c.execute("SELECT points FROM users WHERE telegram_id=?", (user_id,))
        points = c.fetchone()[0]
        await query.message.reply_text(f"⭐ You have {points} points.")
    elif query.data == 'referral':
        await query.message.reply_text(f"🔗 Share this referral link: https://t.me/{context.bot.username}?start={user_id}")
    conn.close()
    await query.answer()

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT xbet_id FROM users WHERE telegram_id=?", (user_id,))
    row = c.fetchone()

    if row and row[0] is None:
        if text.isdigit() and 9 <= len(text) <= 13:
            c.execute("UPDATE users SET xbet_id=? WHERE telegram_id=?", (text, user_id))
            conn.commit()
            await update.message.reply_text("✅ Enter deposit amount (minimum 1000 MMK):")
        else:
            await update.message.reply_text("❌ Invalid ID. Please enter 9–13 digit number:")
    elif row:
        if text.isdigit() and int(text) >= 1000:
            amount = int(text)
            context.user_data['amount'] = amount

            buttons = [[InlineKeyboardButton(bank, callback_data=f"bank_{i}")] for i, bank in enumerate(banks)]
            await update.message.reply_text("🏦 Select a bank:",
                                            reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await update.message.reply_text("❌ Invalid amount. Please enter ≥1000 MMK:")
    conn.close()

async def bank_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bank_index = int(query.data.split("_")[1])
    selected_bank = banks[bank_index]

    context.user_data['bank'] = selected_bank
    await query.message.reply_text("📎 Please send your payment slip (photo or document).")
    await query.answer()

async def slip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    amount = context.user_data.get('amount')
    bank = context.user_data.get('bank')

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT xbet_id FROM users WHERE telegram_id=?", (user_id,))
    xbet_id = c.fetchone()[0]

    caption = (
        f"🧾 New Deposit Request\n"
        f"👤 @{username}\n"
        f"🆔 1xBet ID: {xbet_id}\n"
        f"💰 Amount: {amount} MMK\n"
        f"🏦 Bank: {bank}"
    )

    file = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
    sent = await context.bot.send_photo(ADMIN_GROUP_ID, file, caption=caption)

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Take", callback_data=f"take_{user_id}"),
         InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")]
    ])
    await context.bot.edit_message_reply_markup(ADMIN_GROUP_ID, sent.message_id, reply_markup=buttons)

    c.execute("INSERT INTO transactions (telegram_id, amount, bank, status) VALUES (?, ?, ?, ?)",
              (user_id, amount, bank, 'pending'))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Slip sent to admin for review.")

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, target_id = query.data.split("_")
    target_id = int(target_id)

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT amount FROM transactions WHERE telegram_id=? AND status='pending'", (target_id,))
    row = c.fetchone()
    if not row:
        await query.answer("❌ No pending transaction.", show_alert=True)
        conn.close()
        return
    amount = row[0]

    if action == "approve":
        cashback = int(amount * CASHBACK_PERCENT)
        points = amount // 1000 + cashback

        c.execute("UPDATE users SET points=points+? WHERE telegram_id=?", (points, target_id))
        c.execute("UPDATE transactions SET status='approved' WHERE telegram_id=?", (target_id,))
        conn.commit()

        # Referral commission
        c.execute("SELECT referral_id FROM users WHERE telegram_id=?", (target_id,))
        ref_row = c.fetchone()
        if ref_row and ref_row[0]:
            ref_points = int(amount * REFERRAL_PERCENT)
            c.execute("UPDATE users SET points=points+? WHERE telegram_id=?", (ref_points, ref_row[0]))
            conn.commit()

        await context.bot.send_message(target_id,
                                       f"✅ Deposit approved!\n⭐ Points earned: {points}\n🎉 Total points updated!")
        await query.message.edit_caption(query.message.caption + f"\n✅ Approved by admin.")
    elif action == "reject":
        c.execute("UPDATE transactions SET status='rejected' WHERE telegram_id=?", (target_id,))
        conn.commit()
        await context.bot.send_message(target_id, "❌ Your deposit was rejected. Please contact support.")
        await query.message.edit_caption(query.message.caption + f"\n❌ Rejected by admin.")
    elif action == "take":
        await query.answer("🔒 You took this request.", show_alert=True)
    conn.close()
    await query.answer()

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(deposit|points|referral)$"))
    app.add_handler(CallbackQueryHandler(bank_selection, pattern="^bank_"))
    app.add_handler(CallbackQueryHandler(admin_handler, pattern="^(take|approve|reject)_"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, slip_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
