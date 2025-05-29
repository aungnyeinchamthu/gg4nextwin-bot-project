import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID") or -1001234567890)

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            xbet_id TEXT,
            amount INTEGER,
            bank TEXT,
            slip_file TEXT,
            status TEXT DEFAULT 'pending',
            taken_by_admin INTEGER DEFAULT NULL,
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
    await update.message.reply_text("💰 Please enter your 1xBet ID (9–13 digits):")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    text = update.message.text.strip()

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    # Check for existing pending request or rejection
    c.execute("SELECT request_id, xbet_id, amount, bank, rejection_pending_field FROM requests WHERE user_id=? AND status='pending'", (user_id,))
    row = c.fetchone()

    if not row:
        # New request
        if text.isdigit() and 9 <= len(text) <= 13:
            c.execute("INSERT INTO requests (user_id, username, xbet_id) VALUES (?, ?, ?)", (user_id, username, text))
            conn.commit()
            await update.message.reply_text("✅ Enter the amount you want to deposit:")
        else:
            await update.message.reply_text("❌ Please enter a valid 9–13 digit 1xBet ID.")
    else:
        request_id, xbet_id, amount, bank, pending_field = row

        if pending_field:
            # Resubmission after rejection
            if pending_field == 'xbet_id' and text.isdigit() and 9 <= len(text) <= 13:
                c.execute("UPDATE requests SET xbet_id=?, rejection_pending_field=NULL WHERE request_id=?", (text, request_id))
                conn.commit()
                await resend_to_admin(context, c, request_id)
                await update.message.reply_text("✅ Updated ID. Resubmitted to admin.")
            elif pending_field == 'amount' and text.isdigit() and int(text) >= 1000:
                c.execute("UPDATE requests SET amount=?, rejection_pending_field=NULL WHERE request_id=?", (int(text), request_id))
                conn.commit()
                await resend_to_admin(context, c, request_id)
                await update.message.reply_text("✅ Updated amount. Resubmitted to admin.")
            else:
                await update.message.reply_text("❌ Invalid correction. Please try again.")
        elif not amount:
            if text.isdigit() and int(text) >= 1000:
                c.execute("UPDATE requests SET amount=? WHERE request_id=?", (int(text), request_id))
                conn.commit()
                bank_buttons = [[InlineKeyboardButton(bank['name'], callback_data=f"bank_{i}_{request_id}")] for i, bank in enumerate(banks)]
                await update.message.reply_text("🏦 Select a bank:", reply_markup=InlineKeyboardMarkup(bank_buttons))
            else:
                await update.message.reply_text("❌ Please enter a valid amount (minimum 1000 MMK).")

    conn.close()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    if query.data.startswith('bank_'):
        _, bank_index, request_id = query.data.split("_")
        bank = banks[int(bank_index)]
        c.execute("UPDATE requests SET bank=? WHERE request_id=?", (bank['name'], request_id))
        conn.commit()
        await query.message.reply_text(f"✅ Bank selected: {bank['name']} (Account: {bank['account']}). Please send your slip.")
    elif query.data.startswith(('take_', 'approve_', 'reject_')):
        action, request_id = query.data.split("_", 1)
        c.execute("SELECT user_id, taken_by_admin FROM requests WHERE request_id=?", (request_id,))
        row = c.fetchone()
        if not row:
            await query.answer("❌ Request not found.", show_alert=True)
            conn.close()
            return
        user_id, taken_by = row
        admin_id = query.from_user.id
        admin_username = query.from_user.username or f"admin_{admin_id}"

        if action == 'take':
            if taken_by:
                await query.answer("❌ Already taken.", show_alert=True)
            else:
                c.execute("UPDATE requests SET taken_by_admin=? WHERE request_id=?", (admin_id, request_id))
                conn.commit()
                await query.answer("✅ Taken.")
                await context.bot.send_message(ADMIN_GROUP_ID, f"🛡️ @{admin_username} has taken request {request_id}.")
        elif taken_by != admin_id:
            await query.answer("❌ Only the assigned admin can perform this action.", show_alert=True)
        elif action == 'approve':
            c.execute("UPDATE requests SET status='approved' WHERE request_id=?", (request_id,))
            conn.commit()
            await context.bot.send_message(user_id, "✅ Your deposit has been approved! 🎉")
            await query.answer("✅ Approved.")
        elif action == 'reject':
            reject_buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("Wrong ID", callback_data=f"reject_id_{request_id}")],
                [InlineKeyboardButton("Wrong Amount", callback_data=f"reject_amount_{request_id}")],
                [InlineKeyboardButton("Wrong Slip", callback_data=f"reject_slip_{request_id}")]
            ])
            await query.message.reply_text(f"❌ Select rejection reason for request {request_id}:", reply_markup=reject_buttons)
            await query.answer("❌ Rejection reason.")

    elif query.data.startswith(('reject_id_', 'reject_amount_', 'reject_slip_')):
        reason, request_id = query.data.split("_", 1)
        c.execute("SELECT user_id FROM requests WHERE request_id=?", (request_id,))
        row = c.fetchone()
        if not row:
            await query.answer("❌ Request not found.", show_alert=True)
            conn.close()
            return
        user_id = row[0]
        if reason == 'reject_id':
            c.execute("UPDATE requests SET rejection_pending_field='xbet_id' WHERE request_id=?", (request_id,))
            await context.bot.send_message(user_id, "❌ Your ID was wrong. Please provide the correct 1xBet ID:")
        elif reason == 'reject_amount':
            c.execute("UPDATE requests SET rejection_pending_field='amount' WHERE request_id=?", (request_id,))
            await context.bot.send_message(user_id, "❌ Your amount was wrong. Please provide the correct amount:")
        elif reason == 'reject_slip':
            c.execute("UPDATE requests SET rejection_pending_field='slip_file' WHERE request_id=?", (request_id,))
            await context.bot.send_message(user_id, "❌ Your slip was wrong. Please resend the slip.")
        conn.commit()
        await query.answer("❌ Rejection reason sent.")

    conn.close()

async def slip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT request_id, rejection_pending_field FROM requests WHERE user_id=? AND status='pending'", (user_id,))
    row = c.fetchone()
    if not row:
        await update.message.reply_text("❌ No pending request found.")
        conn.close()
        return

    request_id, pending_field = row
    file_id = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id

    if pending_field == 'slip_file':
        c.execute("UPDATE requests SET slip_file=?, rejection_pending_field=NULL WHERE request_id=?", (file_id, request_id))
        conn.commit()
        await resend_to_admin(context, c, request_id)
        await update.message.reply_text("✅ Slip updated. Resubmitted to admin.")
    else:
        c.execute("UPDATE requests SET slip_file=? WHERE request_id=?", (file_id, request_id))
        conn.commit()
        caption = f"🧾 Request {request_id} ready for admin."
        sent = await context.bot.send_photo(ADMIN_GROUP_ID, file_id, caption=caption)
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔒 Take", callback_data=f"take_{request_id}")],
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{request_id}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{request_id}")]
        ])
        await context.bot.edit_message_reply_markup(ADMIN_GROUP_ID, sent.message_id, reply_markup=buttons)
        await update.message.reply_text("✅ Slip sent to admin.")

    conn.close()

async def resend_to_admin(context, c, request_id):
    c.execute("SELECT user_id, username, xbet_id, amount, bank, slip_file FROM requests WHERE request_id=?", (request_id,))
    row = c.fetchone()
    if not row:
        return
    user_id, username, xbet_id, amount, bank, slip_file = row
    caption = (
        f"🆕 Resubmitted Request {request_id}\n"
        f"👤 User: @{username}\n"
        f"🆔 1xBet ID: {xbet_id}\n"
        f"💰 Amount: {amount}\n"
        f"🏦 Bank: {bank}"
    )
    sent = await context.bot.send_photo(ADMIN_GROUP_ID, slip_file, caption=caption)
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Take", callback_data=f"take_{request_id}")],
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{request_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{request_id}")]
    ])
    await context.bot.edit_message_reply_markup(ADMIN_GROUP_ID, sent.message_id, reply_markup=buttons)

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
