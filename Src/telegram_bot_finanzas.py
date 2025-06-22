# Librerías
import logging
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# -------------------------------
logging.basicConfig(level=logging.INFO)

# Estados del flujo
DESCRIPCION, MONTO, PAGADOR, DEUDORES, INCLUIR_PAGADOR, METODO_PAGO, CONFIRMACION = range(7)

# Constantes
NOMBRES = ["Óscar", "Bichos", "Yetro"]
BICHOS_EQUIVALENCIA = 2
METODOS = ["Santander Oro", "Rappi", "BBVA", "LikeU", "Banamex", "Efectivo"]

# Inicializa Google Sheets
def init_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("../Credenciales/arlqn-338002-4f7192d1576d.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("dineros_amigos").worksheet("Hoja1")
    return sheet

# -------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Usa /gasto para registrar un nuevo gasto o /saldo para ver quién debe a quién.")

async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("¿Cuál es la descripción del gasto?")
    return DESCRIPCION

async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["descripcion"] = update.message.text
    await update.message.reply_text("¿Cuál fue el monto total? (Ej: 1234.56")
    return MONTO

async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["monto"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Por favor, escribe un monto válido (ej. 250)")
        return MONTO

    keyboard = [
        [InlineKeyboardButton(nombre, callback_data=nombre) for nombre in NOMBRES],
        [InlineKeyboardButton("Otro", callback_data="Otro")],
    ]
    await update.message.reply_text("¿Quién pagó?", reply_markup=InlineKeyboardMarkup(keyboard))
    return PAGADOR

async def recibir_pagador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pagador = query.data
    context.user_data["pagador"] = pagador
    context.user_data["deudores"] = []

    keyboard = [
        [InlineKeyboardButton(nombre, callback_data=nombre) for nombre in NOMBRES],
        [InlineKeyboardButton("Todos", callback_data="Todos")],
        [InlineKeyboardButton("Listo", callback_data="Listo")],
        [InlineKeyboardButton("Otro", callback_data="Otro")],
    ]
    await query.edit_message_text("¿Quiénes deben pagar?", reply_markup=InlineKeyboardMarkup(keyboard))
    return DEUDORES

async def recibir_deudores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "Listo":
        keyboard = [
            [InlineKeyboardButton("Sí ✅", callback_data="si")],
            [InlineKeyboardButton("No ❌", callback_data="no")],
        ]
        await query.edit_message_text("¿Quieres incluir al pagador como deudor?", reply_markup=InlineKeyboardMarkup(keyboard))
        return INCLUIR_PAGADOR

    elif data == "Todos":
        deudores = list(NOMBRES)
        if context.user_data["pagador"] in deudores:
            deudores.remove(context.user_data["pagador"])
        context.user_data["deudores"] = deudores

        keyboard = [
            [InlineKeyboardButton(nombre, callback_data=nombre) for nombre in NOMBRES],
            [InlineKeyboardButton("Todos", callback_data="Todos")],
            [InlineKeyboardButton("Listo", callback_data="Listo")],
            [InlineKeyboardButton("Otro", callback_data="Otro")],
        ]
        await query.edit_message_text(
            "Selecciona 'Listo' para continuar o agrega más personas.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return DEUDORES

    elif data == "Otro":
        await query.edit_message_text("Escribe el nombre del deudor extra.")
        return DEUDORES

    else:
        if data not in context.user_data["deudores"]:
            context.user_data["deudores"].append(data)

        keyboard = [
            [InlineKeyboardButton(nombre, callback_data=nombre) for nombre in NOMBRES],
            [InlineKeyboardButton("Todos", callback_data="Todos")],
            [InlineKeyboardButton("Listo", callback_data="Listo")],
            [InlineKeyboardButton("Otro", callback_data="Otro")],
        ]

        await query.edit_message_text(
            f"{data} agregado. Sigue eligiendo o presiona 'Listo'.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return DEUDORES

async def agregar_deudor_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nuevo = update.message.text
    if nuevo not in context.user_data["deudores"]:
        context.user_data["deudores"].append(nuevo)

    keyboard = [
        [InlineKeyboardButton(nombre, callback_data=nombre) for nombre in NOMBRES],
        [InlineKeyboardButton("Todos", callback_data="Todos")],
        [InlineKeyboardButton("Listo", callback_data="Listo")],
        [InlineKeyboardButton("Otro", callback_data="Otro")],
    ]
    await update.message.reply_text("¿Quiénes deben pagar?", reply_markup=InlineKeyboardMarkup(keyboard))
    return DEUDORES

async def incluir_pagador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    incluir = query.data == "si"
    pagador = context.user_data["pagador"]
    if incluir and pagador not in context.user_data["deudores"]:
        context.user_data["deudores"].append(pagador)
    elif not incluir and pagador in context.user_data["deudores"]:
        context.user_data["deudores"].remove(pagador)

    if pagador == "Óscar":
        keyboard = [[InlineKeyboardButton(m, callback_data=m)] for m in METODOS]
        await query.edit_message_text("¿Con qué método pagó Óscar?", reply_markup=InlineKeyboardMarkup(keyboard))
        return METODO_PAGO

    return await mostrar_confirmacion(query, context)

async def recibir_metodo_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["metodo_pago"] = query.data
    return await mostrar_confirmacion(query, context)

async def mostrar_confirmacion(query, context):
    descripcion = context.user_data["descripcion"]
    monto = context.user_data["monto"]
    pagador = context.user_data["pagador"]
    deudores = context.user_data["deudores"]

    total_personas = sum(2 if d == "Bichos" else 1 for d in deudores)
    monto_por_persona = round(monto / total_personas, 2)

    resumen = f"📌 *{descripcion}*\n💰 Monto total: ${monto}\n👤 Pagó: {pagador}\n"
    if pagador == "Óscar" and "metodo_pago" in context.user_data:
        resumen += f"🏦 Método: {context.user_data['metodo_pago']}\n"

    resumen += "💸 Deudores:\n"
    for d in deudores:
        unidades = 2 if d == "Bichos" else 1
        resumen += f"• {d} paga ${monto_por_persona * unidades:.2f}\n"

    keyboard = [[InlineKeyboardButton("Confirmar ✅", callback_data="confirmar")]]
    await query.edit_message_text(resumen, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRMACION

async def confirmar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

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

    await query.edit_message_text("¡Gasto registrado exitosamente! ✅")
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

    resumen = "💳 *Saldos pendientes:*\n"
    for deudor in balance:
        for acreedor, monto in balance[deudor].items():
            contraparte = balance.get(acreedor, {}).get(deudor, 0)
            neto = monto - contraparte
            if neto > 0:
                resumen += f"• {deudor} → {acreedor}: ${round(neto, 2)}\n"

    await update.message.reply_text(resumen or "¡Todo está saldado!", parse_mode="Markdown")

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gasto", gasto)],
        states={
            DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)],
            MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto)],
            PAGADOR: [CallbackQueryHandler(recibir_pagador)],
            DEUDORES: [
                CallbackQueryHandler(recibir_deudores),
                MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_deudor_manual),
            ],
            INCLUIR_PAGADOR: [CallbackQueryHandler(incluir_pagador)],
            METODO_PAGO: [CallbackQueryHandler(recibir_metodo_pago)],
            CONFIRMACION: [CallbackQueryHandler(confirmar_gasto)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("saldo", saldo))
    app.add_handler(CommandHandler("start", start))

    app.run_polling()

# Ejecuta el bot
main()
