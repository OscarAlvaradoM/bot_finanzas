# handlers/saldo.py
from telegram import Update
from telegram.ext import ContextTypes
from repositories.sheets_repository import fetch_movements
from services.finance_service import build_balance_summary

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Calculando saldos...")
    movements = fetch_movements()
    resumen = build_balance_summary(movements)
    await update.message.reply_text(resumen, parse_mode="Markdown")
