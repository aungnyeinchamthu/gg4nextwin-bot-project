import os
import sqlite3
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID")) or -1001234567890

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            request_id TEXT PRIMARY KEY,
            user_id INTEGER,
            username TEXT,
            xbet_id TEXT,
            amount INTEGER,
            bank TEXT,
            slip_file TEXT,
            status TEXT DEFAULT 'pending',
            rejection_pending_field TEXT DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()

banks = [
    {"name": "KBZ Bank", "account": "123-456-789"},
    {"name": "AYA Bank", "account": "987-654-321"},
    {"name": "CB Bank", "account": "555-666-777"},
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("💰 Deposit", callback_data='deposit_start')]]
    await update.message.reply_text("👋 Welcome! Please choose an option:",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username or f"user_{user_id}"

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    if query.data == 'deposit_start':
        request_id = str(uuid.uuid4())
        c.execute("INSERT INTO requests (request_id, user_id, username) VALUES (?, ?, ?)",
                  (request_id, user_id, username))
        conn.commit()
        await query.message.reply_text("Please enter your 1xBet ID (9–13 digits):")

    elif query.data.startswith('bank_'):
        _, bank_index, request_id = query.data.split("_")
        bank_index = int(bank_index)
        selected_bank = banks[bank_index]

        c.execute("UPDATE requests SET bank=? WHERE request_id=?", (selected_bank['name'], request_id))
        conn.commit()
        await query.message.reply_text(
            f"✅ You selected {selected_bank['name']} (Account: {selected_bank['account']}).\n"
            f"Please send your deposit slip as an image or document."
        )

    elif query.data.startswith(('take_', 'approve_', 'reject_')):
        action, req_id = query.data.split("_", 1)
        c.execute("SELECT user_id FROM requests WHERE request_id=?", (req_id,))
        row = c.fetchone()
        if not row:
            await query.answer("❌ Request not found.", show_alert=True)
            conn.close()
            return
        target_user = row[0]
        admin_username = query.from_user.username or f"admin_{query.from_user.id}"

        if action == "take":
            await context.bot.send_message(ADMIN_GROUP_ID, f"🛡️ @{admin_username} has taken request {req_id}.")
            await query.answer("Taken.")

        elif action == "approve":
            c.execute("UPDATE requests SET status='approved', rejection_pending_field=NULL WHERE request_id=?", (req_id,))
            conn.commit()
            await context.bot.send_message(target_user, "✅ Your deposit has been approved! 🎉")
            await query.answer("Approved.")

        elif action == "reject":
            reject_buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("Wrong ID", callback_data=f"reject_id_{req_id}")],
                [InlineKeyboardButton("Wrong Amount", callback_data=f"reject_amount_{req_id}")],
                [InlineKeyboardButton("Wrong Slip", callback_data=f"reject_slip_{req_id}")]
            ])
            await query.message.reply_text(f"❌ Select rejection reason for request {req_id}:",
                                           reply_markup=reject_buttons)
            await query.answer("Rejection reason requested.")

    elif query.data.startswith(('reject_id_', 'reject_amount_', 'reject_slip_')):
        parts = query.data.split("_")
        reason = parts[1]
        req_id = '_'.join(parts[2:])

        c.execute("SELECT user_id FROM requests WHERE request_id=?", (req_id,))
        row = c.fetchone()
        if not row:
            await query.answer("❌ Request not found.", show_alert=True)
            conn.close()
            return
        target_user = row[0]

        c.execute("UPDATE requests SET rejection_pending_field=? WHERE request_id=?", (reason, req_id))
        conn.commit()

        if reason == 'id':
            await context.bot.send_message(target_user, "❌ Your ID was incorrect. Please re-enter your 1xBet ID:")
        elif reason == 'amount':
            await context.bot.send_message(target_user, "❌ Your amount was incorrect. Please re-enter your amount:")
        elif reason == 'slip':
            await context.bot.send_message(target_user, "❌ Your slip was incorrect. Please resend your slip:")

        await query.answer("Rejection reason sent to user.")
    conn.close()

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT request_id, rejection_pending_field FROM requests WHERE user_id=? AND status='pending'",
              (user_id,))
    row = c.fetchone()

    if not row:
        await update.message.reply_text("❌ Please start a new deposit with /start.")
        conn.close()
        return

    request_id, pending_field = row

    if pending_field:
        if pending_field == 'id':
            if text.isdigit() and 9 <= len(text) <= 13:
                c.execute("UPDATE requests SET xbet_id=?, rejection_pending_field=NULL WHERE request_id=?",
                          (text, request_id))
                conn.commit()
                await resubmit_to_admin(context, c, request_id)
            else:
                await update.message.reply_text("❌ Invalid ID format. Please enter a 9–13 digit number.")
        elif pending_field == 'amount':
            if text.isdigit() and int(text) >= 1000:
                c.execute("UPDATE requests SET amount=?, rejection_pending_field=NULL WHERE request_id=?",
                          (int(text), request_id))
                conn.commit()
                await resubmit_to_admin(context, c, request_id)
            else:
                await update.message.reply_text("❌ Invalid amount. Please enter a number ≥ 1000.")
    else:
        # Regular flow
        c.execute("SELECT xbet_id, amount FROM requests WHERE request_id=?", (request_id,))
        xbet_id, amount = c.fetchone()

        if not xbet_id:
            if text.isdigit() and 9 <= len(text) <= 13:
                c.execute("UPDATE requests SET xbet_id=? WHERE request_id=?", (text, request_id))
                conn.commit()
                await update.message.reply_text("✅ Enter the amount you want to deposit:")
            else:
                await update.message.reply_text("❌ Invalid ID format. Please enter a 9–13 digit number.")
        elif not amount:
            if text.isdigit() and int(text) >= 1000:
                c.execute("UPDATE requests SET amount=? WHERE request_id=?", (int(text), request_id))
                conn.commit()
                bank_buttons = [[InlineKeyboardButton(bank['name'], callback_data=f"bank_{i}_{request_id}")]
                                for i, bank in enumerate(banks)]
                await update.message.reply_text("🏦 Select a bank:", reply_markup=InlineKeyboardMarkup(bank_buttons))
            else:
                await update.message.reply_text("❌ Invalid amount. Please enter a number ≥ 1000.")

    conn.close()

async def slip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT request_id FROM requests WHERE user_id=? AND status='pending'", (user_id,))
    row = c.fetchone()
    if not row:
        await update.message.reply_text("❌ No pending request found. Please start over.")
        conn.close()
        return

    request_id = row[0]
    file_id = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id

    c.execute("UPDATE requests SET slip_file=?, rejection_pending_field=NULL WHERE request_id=?", (file_id, request_id))
    conn.commit()

    await resubmit_to_admin(context, c, request_id)
    await update.message.reply_text("✅ Slip sent to admin for review.")
    conn.close()

async def resubmit_to_admin(context, c, request_id):
    c.execute("SELECT user_id, username, xbet_id, amount, bank, slip_file FROM requests WHERE request_id=?",
              (request_id,))
    user_id, username, xbet_id, amount, bank, slip_file = c.fetchone()
    caption = (
        f"🧾 Request ID: {request_id}\n"
        f"👤 User: @{username}\n"
        f"🆔 1xBet ID: {xbet_id}\n"
        f"💰 Amount: {amount}\n"
        f"🏦 Bank: {bank}"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Take", callback_data=f"take_{request_id}")],
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{request_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{request_id}")]
    ])
    await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=caption, reply_markup=buttons)

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, slip_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
