from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.message:
        await update.message.reply_text("❌ Operación cancelada.")
    else:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text("❌ Operación cancelada.")
    return ConversationHandler.END