# Te prepararé un archivo completo con el nuevo flujo de conversación más explícito,
# donde cada paso queda como mensaje individual en el chat y se ajustan los botones y estados.

from dotenv import load_dotenv
import os
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

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# -------------------------------
logging.basicConfig(level=logging.INFO)

# Estados del flujo
DESCRIPCION, MONTO, PAGADOR, DEUDORES, NOMBRE_DEUDOR_EXTRA, INCLUIR_PAGADOR, METODO_PAGO, CONFIRMACION = range(8)

# Constantes
NOMBRES = ["Óscar", "Bichos", "Yetro"]
OPCIONES_PAGADORES = ["Óscar", "Yetro", "Bichos", "Fabos"]
OPCIONES_DEUDORES = ["Óscar", "Yetro", "Bichos", "Fabos"]
BICHOS_EQUIVALENCIA = 2
FABOS_EQUIVALENCIA = 2
METODOS = ["Santander Oro", "Rappi", "BBVA", "LikeU", "Banamex", "Efectivo"]
NOMBRE_PAGADOR_MANUAL = 99  # Usa un número que no choque con los otros estados

# Al inicio
ESPERANDO_EDICION = 8

# Inicializa Google Sheets
def init_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(os.getenv("GOOGLE_CREDS_PATH"), scope)
    client = gspread.authorize(creds)
    sheet = client.open("bd_amigos").worksheet("Hoja1")
    return sheet

# -------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Usa /gasto para registrar un nuevo gasto o /saldo para ver quién debe a quién.")

async def cancelar_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()  # Limpiar cualquier dato temporal del usuario
    if update.message:
        await update.message.reply_text("Operación cancelada. Puedes empezar de nuevo cuando gustes. ❌")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operación cancelada. Puedes empezar de nuevo cuando gustes. ❌")
    return ConversationHandler.END

# async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     context.user_data.clear()
#     await update.message.reply_text("📌 ¿Cuál es la descripción del gasto?")
#     return DESCRIPCION

async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Inicia el flujo de ingreso de gasto.
    Limpia los datos del usuario y pregunta por la descripción del gasto.
    """
    context.user_data.clear()

    mensaje = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="📌 ¿Cuál es la descripción del gasto?\n\nResponde directamente a este mensaje.",
        parse_mode="Markdown"
    )

    context.user_data["mensaje_descripcion_id"] = mensaje.message_id

    return DESCRIPCION

# async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """
#     Lo que esperamos de respuesta cuando preguntamos por la descripción del gasto. 
#     Muestra después de haber recibido esa respuesta, la pregunta del monto total.
#     """
#     context.user_data["descripcion"] = update.message.text
#     await update.message.reply_text("💰 ¿Cuál fue el monto total? (Ej: 1234.56)")
#     return MONTO

async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Recibe la descripción del gasto, validando que esté respondiendo al mensaje esperado.
    Luego pregunta por el monto total.
    """
    mensaje_esperado = context.user_data.get("mensaje_descripcion_id")
    if update.message.reply_to_message and update.message.reply_to_message.message_id != mensaje_esperado:
        await update.message.reply_text("Por favor, responde directamente al mensaje que pregunta por la descripción del gasto.")
        return DESCRIPCION

    context.user_data["descripcion"] = update.message.text

    mensaje_monto = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="💰 ¿Cuál fue el monto total? (ej. 1234.56)\n\nResponde directamente a este mensaje.",
        parse_mode="Markdown"
    )

    context.user_data["mensaje_monto_id"] = mensaje_monto.message_id
    return MONTO

async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Acá recibimos la respuesta a la pregunta del monto.
    Y luego creamos la pregunta sobre quién pagó en esta ocasión el gasto.
    """
    try:
        context.user_data["monto"] = float(update.message.text.replace("$", "").replace(",", ""))
    except ValueError:
        await update.message.reply_text("Por favor, escribe un monto válido (ej. 250.00)")
        return MONTO

    keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in OPCIONES_PAGADORES + ["Otro"]]
    await update.message.reply_text("👤 ¿Quién pagó?", reply_markup=InlineKeyboardMarkup(keyboard))
    return PAGADOR

async def recibir_pagador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    opcion = query.data

    if opcion == "Otro":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✍️ Escribe el nombre del pagador:")
        return NOMBRE_PAGADOR_MANUAL
    else:
        context.user_data["pagador"] = opcion
        context.user_data["deudores"] = []
        context.user_data["extra_deudores"] = []
        context.user_data["primer_pregunta_deudores"] = True  # <- MARCAMOS PRIMERA PREGUNTA

        nombres_disponibles = [n for n in OPCIONES_DEUDORES if n != opcion]

        keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in nombres_disponibles]
        fila_extra = [InlineKeyboardButton("Los 4", callback_data="Todos"), InlineKeyboardButton("Otro", callback_data="Otro")]

        # NO mostramos "Listo" la primera vez
        # (se mostrará más adelante desde recibir_deudores)
        keyboard.append(fila_extra)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="💸 ¿Quiénes deben pagar?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return DEUDORES


async def recibir_pagador_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Recibe el nombre del pagador cuando elige 'Otro' y continúa al paso de seleccionar deudores.
    """
    pagador = update.message.text.strip()
    if not pagador:
        await update.message.reply_text("❌ Nombre no válido. Intenta nuevamente.")
        return NOMBRE_PAGADOR_MANUAL  # Este es un nuevo estado que debes definir.

    context.user_data["pagador"] = pagador
    context.user_data["deudores"] = []
    context.user_data["extra_deudores"] = []

    # Construimos el teclado de deudores excluyendo al pagador
    nombres_disponibles = [n for n in OPCIONES_DEUDORES if n != pagador]
    keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in nombres_disponibles]
    keyboard.append([
        InlineKeyboardButton("Los 4", callback_data="Todos"),
        InlineKeyboardButton("Otro", callback_data="Otro"),
        InlineKeyboardButton("Listo", callback_data="Listo")
    ])

    await update.message.reply_text(
        f"👤 Nuevo pagador registrado: *{pagador}*\n\n💸 ¿Quiénes deben pagar?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DEUDORES

async def recibir_deudores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    pagador = context.user_data["pagador"]
    deudores = context.user_data["deudores"]

    if data == "Listo":
        keyboard = [
            [InlineKeyboardButton("Sí ✅", callback_data="si")],
            [InlineKeyboardButton("No ❌", callback_data="no")]
        ]
        await context.bot.send_message(chat_id=update.effective_chat.id, text="¿El pagador también es deudor?", reply_markup=InlineKeyboardMarkup(keyboard))
        return INCLUIR_PAGADOR

    elif data == "Todos":
        todos = [n for n in ["Óscar", "Yetro", "Bichos"] if n != pagador]
        context.user_data["deudores"] = list(set(deudores + todos))
        context.user_data["primer_pregunta_deudores"] = False  # ✅ Ya se agregó alguien
        mensaje = f"✅ Se agregaron: {', '.join(todos)}\n\n"

    elif data == "Otro":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✍️ Escribe el nombre del otro deudor:")
        return NOMBRE_DEUDOR_EXTRA

    else:
        if data not in deudores and data != pagador:
            context.user_data["deudores"].append(data)
            context.user_data["primer_pregunta_deudores"] = False  # ✅ Ya se agregó alguien
            mensaje = f"✅ *{data}* fue agregado como deudor.\n\n"
        else:
            mensaje = f"⚠️ *{data}* ya fue agregado o es el pagador.\n\n"

    # Recalcular opciones válidas
    nombres_disponibles = [
        n for n in OPCIONES_DEUDORES if n not in context.user_data["deudores"] and n != pagador
    ]

    # Si alguno de los 3 ya fue elegido, quitamos "Los 4"
    grupo_4 = {"Óscar", "Yetro", "Bichos"}
    ya_elegidos = set(context.user_data["deudores"])
    mostrar_todos = grupo_4.isdisjoint(ya_elegidos)

    keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in nombres_disponibles]

    fila_extra = []
    if mostrar_todos:
        fila_extra.append(InlineKeyboardButton("Los 4", callback_data="Todos"))
    fila_extra.append(InlineKeyboardButton("Otro", callback_data="Otro"))

    # ✅ Mostramos "Listo" solo si ya pasó la primera vez
    if not context.user_data.get("primer_pregunta_deudores", True):
        fila_extra.append(InlineKeyboardButton("Listo", callback_data="Listo"))

    keyboard.append(fila_extra)

    mensaje += "Sigue eligiendo deudores o presiona *Listo* para continuar."
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=mensaje,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DEUDORES

async def agregar_deudor_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nuevo = update.message.text.strip()
    if nuevo:
        if nuevo not in context.user_data["deudores"]:
            context.user_data["deudores"].append(nuevo)
            mensaje = f"✅ *{nuevo}* fue agregado como deudor.\n\n"
        else:
            mensaje = f"⚠️ *{nuevo}* ya está en la lista de deudores.\n\n"
    else:
        mensaje = "❌ Nombre no válido. Intenta nuevamente.\n\n"

    mensaje += "Sigue eligiendo deudores o presiona *Listo* para continuar."

    # Creamos el nuevo teclado quitando los ya seleccionados
    nombres_faltantes = [n for n in OPCIONES_DEUDORES if n not in context.user_data["deudores"]]
    keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in nombres_faltantes]
    keyboard.append([
        InlineKeyboardButton("Los 4", callback_data="Todos"),
        InlineKeyboardButton("Otro", callback_data="Otro"),
        InlineKeyboardButton("Listo", callback_data="Listo")
    ])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=mensaje,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DEUDORES

async def incluir_pagador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pagador = context.user_data["pagador"]
    if query.data == "si" and pagador not in context.user_data["deudores"]:
        context.user_data["deudores"].append(pagador)

    if pagador == "Óscar":
        keyboard = [[InlineKeyboardButton(m, callback_data=m)] for m in METODOS]
        await context.bot.send_message(chat_id=update.effective_chat.id, text="🏦 ¿Con qué método pagó Óscar?", reply_markup=InlineKeyboardMarkup(keyboard))
        return METODO_PAGO

    return await mostrar_confirmacion(update, context)

async def recibir_metodo_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["metodo_pago"] = query.data
    return await mostrar_confirmacion(update, context)

async def mostrar_confirmacion(update, context):
    """
    Aquí mostramos el resumen de lo que hicimos
    Preguntamos al usuario si desea confirmar, cancelar o editar algún concepto
    """
    descripcion = context.user_data["descripcion"]
    monto = context.user_data["monto"]
    pagador = context.user_data["pagador"]
    deudores = context.user_data["deudores"]
    metodo = context.user_data.get("metodo_pago", None)

    total_personas = sum(2 if d in ["Bichos", "Fabos"] else 1 for d in deudores)
    monto_por_persona = round(monto / total_personas, 2)

    resumen = f"📌 *{descripcion}*\n💰 Monto total: ${monto:,}\n👤 Pagó: {pagador}\n"
    if metodo:
        resumen += f"🏦 Método: {metodo}\n"
    resumen += "💸 Deudores:\n"
    for d in deudores:
        unidades = 2 if d in ["Bichos", "Fabos"] else 1
        resumen += f"• {d} paga ${monto_por_persona * unidades:,.2f}\n"

    keyboard = [
            [InlineKeyboardButton("Confirmar ✅", callback_data="confirmar")],
            [InlineKeyboardButton("Cancelar ❌", callback_data="cancelar")],
            #[InlineKeyboardButton("Editar ✏️", callback_data="editar")]
        ]
    await context.bot.send_message(chat_id=update.effective_chat.id, text=resumen, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRMACION

async def confirmar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Si confirmamos la transacción escribirmos en la hoja de google sheets
    """
    query = update.callback_query
    await query.answer()

    sheet = init_gsheet()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    descripcion = context.user_data["descripcion"]
    monto = context.user_data["monto"]
    pagador = context.user_data["pagador"]
    metodo = context.user_data.get("metodo_pago", "")
    deudores = context.user_data["deudores"]
    total_personas = sum(2 if d in ["Bichos", "Fabos"] else 1 for d in deudores)
    monto_por_persona = round(monto / total_personas, 2)

    for d in deudores:
        unidades = 2 if d in ["Bichos", "Fabos"] else 1
        row = [descripcion, monto_por_persona * unidades, d, pagador, now]
        if pagador == "Óscar":
            row.append(metodo)
        sheet.append_row(row)

    await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Gasto registrado exitosamente! ✅")
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Operación cancelada. ❌")
    return ConversationHandler.END


# -------------------- Aquí ya comienza lo del botón para revisar el saldo -------------------------

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheet = init_gsheet()
    data = sheet.get_all_records()
    balance = {}

    await update.message.reply_text("Calculando saldo...", parse_mode="Markdown")


    for row in data:
        deudor = row["Deudor"]
        acreedor = row["Prestador"]
        monto = float(str(row["Monto"]).replace('$', '').replace(',',''))
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

    await update.message.reply_text(resumen or "¡Todo está saldado!", parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gasto", gasto)],
        states={
            DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)],
            MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto)],
            PAGADOR: [CallbackQueryHandler(recibir_pagador)],
            NOMBRE_PAGADOR_MANUAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_pagador_manual)],
            DEUDORES: [CallbackQueryHandler(recibir_deudores)],
            NOMBRE_DEUDOR_EXTRA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_deudor_manual)],
            INCLUIR_PAGADOR: [CallbackQueryHandler(incluir_pagador)],
            METODO_PAGO: [CallbackQueryHandler(recibir_metodo_pago)],
            CONFIRMACION: [CallbackQueryHandler(confirmar_gasto, pattern="^confirmar$"),
                        CallbackQueryHandler(cancelar, pattern="^cancelar$"),
                        #CallbackQueryHandler(editar_gasto, pattern="^editar$"),
                        ],
            #ESPERANDO_EDICION: [CallbackQueryHandler(redirigir_edicion)],

        },
        fallbacks=[CommandHandler("cancelar", cancelar_comando)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("saldo", saldo))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancelar", cancelar_comando))

    app.run_polling()

# Ejecuta el bot
main()