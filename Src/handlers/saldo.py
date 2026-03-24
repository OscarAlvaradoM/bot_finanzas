# handlers/saldo.py
from domain.errors import RepositoryError
from telegram import Update
from telegram.ext import ContextTypes
from repositories.sheets_repository import fetch_movements
from services.finance_service import build_balance_summary

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Calculando saldos...")
    try:
        movements = fetch_movements()
    except RepositoryError:
        await update.message.reply_text("❌ No pude consultar los saldos en este momento. Intenta de nuevo más tarde.")
        return
    resumen = build_balance_summary(movements)
    await update.message.reply_text(resumen, parse_mode="Markdown")
