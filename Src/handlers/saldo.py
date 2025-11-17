# handlers/saldo.py
from telegram import Update
from telegram.ext import ContextTypes
from sheets import init_gsheet

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheet = init_gsheet()
    data = sheet.get_all_records()
    
    balance = {}

    await update.message.reply_text("Calculando saldos...")

    for row in data:
        deudor = row["Deudor"]
        acreedor = row["Prestador"]
        monto = float(str(row["Monto"]).replace("$", "").replace(",", ""))

        balance.setdefault(deudor, {})
        balance.setdefault(acreedor, {})

        balance[deudor][acreedor] = balance[deudor].get(acreedor, 0) + monto

    resumen = "💳 *Saldos pendientes:*\n"

    for deudor in balance:
        for acreedor, monto in balance[deudor].items():
            contraparte = balance.get(acreedor, {}).get(deudor, 0)
            neto = monto - contraparte
            if neto > 0:
                resumen += f"• {deudor} → {acreedor}: ${round(neto, 2):,}\n"

    if resumen.strip() == "💳 *Saldos pendientes:*":
        resumen = "🎉 ¡Todo está saldado!"

    await update.message.reply_text(resumen, parse_mode="Markdown")
