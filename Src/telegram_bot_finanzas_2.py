import logging
import datetime
import os
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, ConversationHandler, filters

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Estados del flujo
DESCRIPCION, MONTO, PAGADOR, DEUDORES, MAS_DEUDORES, INCLUIR_PAGADOR, METODO_PAGO, CONFIRMACION = range(8)

# Constantes
NOMBRES = ["Óscar", "Bichos", "Yetro", "Fabos"]
BICHOS_EQUIVALENCIA = 2
METODOS = ["Santander Oro", "Rappi", "BBVA", "LikeU", "Banamex", "Efectivo"]

# Inicializa Google Sheets
def init_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("dineros_amigos").worksheet("Hoja1")
    return sheet

# Iniciar flujo
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Usa /gasto para registrar un nuevo gasto o /saldo para ver quién debe a quién.")

async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("¿Cuál es la descripción del gasto?", reply_markup=ReplyKeyboardRemove())
    return DESCRIPCION

async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["descripcion"] = update.message.text
    await update.message.reply_text("¿Cuál fue el monto total?")
    return MONTO

async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["monto"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Por favor escribe un número válido.")
        return MONTO

    keyboard = ReplyKeyboardMarkup([["Óscar", "Yetro", "Bichos", "Otro"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("¿Quién pagó?", reply_markup=keyboard)
    return PAGADOR

async def recibir_pagador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pagador"] = update.message.text
    context.user_data["deudores"] = []
    keyboard = ReplyKeyboardMarkup([["Óscar", "Yetro", "Bichos", "Fabos", "Otro", "Listo"]], resize_keyboard=True)
    await update.message.reply_text("Agrega deudores uno por uno. Pulsa 'Listo' al terminar.", reply_markup=keyboard)
    return DEUDORES

async def recibir_deudor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if texto == "Listo":
        keyboard = ReplyKeyboardMarkup([["Sí", "No"]], one_time_keyboard=True, resize_keyboard=True)
        return await update.message.reply_text("¿Quieres incluir al pagador como deudor?", reply_markup=keyboard), INCLUIR_PAGADOR

    context.user_data["deudores"].append(texto)
    return DEUDORES

async def incluir_pagador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Sí":
        pagador = context.user_data["pagador"]
        context.user_data["deudores"].append(pagador)

    if context.user_data["pagador"] == "Óscar":
        keyboard = ReplyKeyboardMarkup([[m] for m in METODOS], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("¿Con qué método pagó Óscar?", reply_markup=keyboard)
        return METODO_PAGO

    return await mostrar_confirmacion(update, context)

async def recibir_metodo_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["metodo_pago"] = update.message.text
    return await mostrar_confirmacion(update, context)

async def mostrar_confirmacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descripcion = context.user_data["descripcion"]
    monto = context.user_data["monto"]
    pagador = context.user_data["pagador"]
    deudores = context.user_data["deudores"]
    total_personas = sum(2 if d == "Bichos" else 1 for d in deudores)
    monto_por_persona = round(monto / total_personas, 2)

    resumen = f"📌 {descripcion}\\n💰 Monto: ${monto}\\n👤 Pagó: {pagador}\\n"
    if pagador == "Óscar" and "metodo_pago" in context.user_data:
        resumen += f"🏦 Método: {context.user_data['metodo_pago']}\\n"

    resumen += "💸 Deudores:\\n"
    for d in deudores:
        unidades = 2 if d == "Bichos" else 1
        resumen += f"• {d} paga ${monto_por_persona * unidades:.2f}\\n"

    keyboard = ReplyKeyboardMarkup([["Confirmar", "Cancelar"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(resumen, reply_markup=keyboard)
    return CONFIRMACION

async def confirmar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Cancelar":
        await update.message.reply_text("Operación cancelada.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    sheet = init_gsheet()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    descripcion = context.user_data["descripcion"]
    monto = context.user_data["monto"]
    pagador = context.user_data["pagador"]
    deudores = context.user_data["deudores"]
    metodo = context.user_data.get("metodo_pago", "")
    total_personas = sum(2 if d == "Bichos" else 1 for d in deudores)
    monto_por_persona = round(monto / total_personas, 2)

    for d in deudores:
        unidades = 2 if d == "Bichos" else 1
        row = [descripcion, monto_por_persona * unidades, d, pagador, now]
        if pagador == "Óscar":
            row.append(metodo)
        sheet.append_row(row)

    await update.message.reply_text("¡Gasto registrado exitosamente! ✅", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheet = init_gsheet()
    data = sheet.get_all_records()
    balance = {}

    for row in data:
        deudor = row["Deudor"]
        acreedor = row["Prestador"]
        monto = float(row["Monto"])
        balance.setdefault(deudor, {})
        balance.setdefault(acreedor, {})
        balance[deudor][acreedor] = balance[deudor].get(acreedor, 0) + monto

    resumen = "💳 *Saldos pendientes:*\\n"
    for deudor in balance:
        for acreedor, monto in balance[deudor].items():
            contraparte = balance.get(acreedor, {}).get(deudor, 0)
            neto = monto - contraparte
            if neto > 0:
                resumen += f"• {deudor} → {acreedor}: ${round(neto, 2)}\\n"

    await update.message.reply_text(resumen or "¡Todo está saldado!", parse_mode="Markdown")

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gasto", gasto)],
        states={
            DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)],
            MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto)],
            PAGADOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_pagador)],
            DEUDORES: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_deudor)],
            INCLUIR_PAGADOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, incluir_pagador)],
            METODO_PAGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_metodo_pago)],
            CONFIRMACION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_gasto)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("saldo", saldo))
    app.add_handler(CommandHandler("start", start))

    app.run_polling()

main()
