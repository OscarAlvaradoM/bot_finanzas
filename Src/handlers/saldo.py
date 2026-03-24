# handlers/saldo.py
from telegram import Update
from telegram.ext import ContextTypes
from repositories.sheets_repository import fetch_records
from services.finance_service import build_balance_summary

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Calculando saldos...")
    data = fetch_records()
    resumen = build_balance_summary(data)
    await update.message.reply_text(resumen, parse_mode="Markdown")
