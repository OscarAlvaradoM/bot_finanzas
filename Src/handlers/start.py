# handlers/start.py
from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! 👋\n\n"
        "Puedo ayudarte a registrar *gastos*, *pagos* y consultar *saldos*.\n\n"
        "Usa:\n"
        "*/gasto* para registrar un gasto\n"
        "*/pago* para registrar un pago\n"
        "*/saldo* para ver quién debe a quién",
        parse_mode="Markdown",
    )
