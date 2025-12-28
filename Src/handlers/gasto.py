from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import datetime
from config import (
    DESCRIPCION, MONTO, PAGADOR, DEUDORES, NOMBRE_DEUDOR_EXTRA,
    INCLUIR_PAGADOR, METODO_PAGO, CONFIRMACION, NOMBRE_PAGADOR_MANUAL,
    OPCIONES_PAGADORES, OPCIONES_DEUDORES, METODOS
)
from sheets import init_gsheet

# Al invocar el comando de /gasto
# Preguntamos por la descripción del gasto
async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    mensaje = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="📌 ¿Cuál es la descripción del gasto?\n\nResponde directamente a este mensaje.",
        parse_mode="Markdown"
    )
    context.user_data["mensaje_descripcion_id"] = mensaje.message_id
    return DESCRIPCION

# Recibimos descripción del mensaje y preguntamos por monto que fue gastado
async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# Recibimos monto y preguntamos por pagador
async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje_esperado = context.user_data.get("mensaje_monto_id")
    if update.message.reply_to_message and update.message.reply_to_message.message_id != mensaje_esperado:
        await update.message.reply_text("Por favor, responde directamente al mensaje que pregunta por el monto.")
        return MONTO

    try:
        context.user_data["monto"] = float(update.message.text.replace("$", "").replace(",", ""))
    except ValueError:
        await update.message.reply_text("Por favor, escribe un monto válido (ej. 250.00)")
        return MONTO

    keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in OPCIONES_PAGADORES]
    keyboard.append([InlineKeyboardButton("Otro", callback_data="Otro")])
    await context.bot.send_message(chat_id=update.effective_chat.id, text="👤 ¿Quién pagó?", reply_markup=InlineKeyboardMarkup(keyboard))
    return PAGADOR

# Recibimos pagador y preguntamos por deudores
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
        context.user_data["primer_pregunta_deudores"] = True

        nombres_disponibles = [n for n in OPCIONES_DEUDORES if n != opcion]

        keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in nombres_disponibles]
        fila_extra = [InlineKeyboardButton("Los 4", callback_data="Todos"), InlineKeyboardButton("Otro", callback_data="Otro")]

        keyboard.append(fila_extra)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="💸 ¿Quiénes deben pagar?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return DEUDORES
# Recibimos deudor manual y preguntamos por deudores
async def recibir_pagador_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pagador = update.message.text.strip()
    if not pagador:
        await update.message.reply_text("❌ Nombre no válido. Intenta nuevamente.")
        return NOMBRE_PAGADOR_MANUAL

    context.user_data["pagador"] = pagador
    context.user_data["deudores"] = []
    context.user_data["extra_deudores"] = []
    nombres_disponibles = [n for n in OPCIONES_DEUDORES if n != pagador]
    keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in nombres_disponibles]
    keyboard.append([
        InlineKeyboardButton("Los 4", callback_data="Todos"),
        InlineKeyboardButton("Otro", callback_data="Otro"),
        InlineKeyboardButton("Listo", callback_data="Listo")
    ])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"👤 Nuevo pagador registrado: *{pagador}*\n\n💸 ¿Quiénes deben pagar?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DEUDORES

# Recibimos deudores y preguntamos si el pagador también es deudor
async def recibir_deudores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    pagador = context.user_data["pagador"]
    deudores = context.user_data.get("deudores", [])

    if data == "Listo":
        keyboard = [
            [InlineKeyboardButton("Sí ✅", callback_data="si")],
            [InlineKeyboardButton("No ❌", callback_data="no")]
        ]
        await context.bot.send_message(chat_id=update.effective_chat.id, text="¿El pagador también es deudor?", reply_markup=InlineKeyboardMarkup(keyboard))
        return INCLUIR_PAGADOR

    elif data == "Los 4 de siempre":
        grupo = ["Óscar", "Yetro", "Bichos"]
        grupo_final = [n for n in grupo if n != pagador]
        context.user_data["deudores"] = list(set(deudores + grupo_final))
        context.user_data["primer_pregunta_deudores"] = False
        mensaje = f"✅ Se agregaron: {', '.join(grupo_final)}\n\n"

    elif data == "Otro":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✍️ Escribe el nombre del otro deudor:")
        return NOMBRE_DEUDOR_EXTRA

    else:
        if data not in deudores and data != pagador:
            context.user_data.setdefault("deudores", []).append(data)
            context.user_data["primer_pregunta_deudores"] = False
            mensaje = f"✅ *{data}* fue agregado como deudor.\n\n"
        else:
            mensaje = f"⚠️ *{data}* ya fue agregado o es el pagador.\n\n"

    nombres_disponibles = [n for n in OPCIONES_DEUDORES if n not in context.user_data.get("deudores", []) and n != pagador]

    grupo_4 = {"Óscar", "Yetro", "Bichos"}
    ya_elegidos = set(context.user_data.get("deudores", []))
    mostrar_todos = grupo_4.isdisjoint(ya_elegidos)

    keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in nombres_disponibles]

    fila_extra = []
    if mostrar_todos:
        fila_extra.append(InlineKeyboardButton("Los 4", callback_data="Los 4 de siempre"))
    fila_extra.append(InlineKeyboardButton("Otro", callback_data="Otro"))

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

# Recibimos deudor extra manualmente y volvemos a preguntar por deudores
async def agregar_deudor_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nuevo = update.message.text.strip()
    if nuevo:
        if nuevo not in context.user_data.get("deudores", []):
            context.user_data.setdefault("deudores", []).append(nuevo)
            mensaje = f"✅ *{nuevo}* fue agregado como deudor.\n\n"
        else:
            mensaje = f"⚠️ *{nuevo}* ya está en la lista de deudores.\n\n"
    else:
        mensaje = "❌ Nombre no válido. Intenta nuevamente.\n\n"

    mensaje += "Sigue eligiendo deudores o presiona *Listo* para continuar."

    nombres_faltantes = [n for n in OPCIONES_DEUDORES if n not in context.user_data.get("deudores", [])]
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

# Recibinmos respuesta de si pagador es deudor y preguntamos por método de pago (en caso de ser Óscar) o confirmación
async def incluir_pagador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pagador = context.user_data["pagador"]
    if query.data == "si" and pagador not in context.user_data.get("deudores", []):
        context.user_data.setdefault("deudores", []).append(pagador)

    if pagador == "Óscar":
        keyboard = [[InlineKeyboardButton(m, callback_data=m)] for m in METODOS]
        await context.bot.send_message(chat_id=update.effective_chat.id, text="🏦 ¿Con qué método pagó Óscar?", reply_markup=InlineKeyboardMarkup(keyboard))
        return METODO_PAGO

    return await mostrar_confirmacion(update, context)

# Si paga Óscar, acá recibimos el método de pago
async def recibir_metodo_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["metodo_pago"] = query.data
    return await mostrar_confirmacion(update, context)

# Mostramos el resumen del gasto y pedimos confirmación o cancelación
async def mostrar_confirmacion(update, context):
    descripcion = context.user_data.get("descripcion","")
    monto = context.user_data.get("monto",0)
    pagador = context.user_data.get("pagador","")
    deudores = context.user_data.get("deudores",[])
    metodo = context.user_data.get("metodo_pago", None)

    total_personas = sum(2 if d in ["Bichos", "Fabos"] else 1 for d in deudores) or 1
    monto_por_persona = round(monto / total_personas, 2)

    resumen = f"📌 *{descripcion}*\n💰 Monto total: ${monto:,.2f}\n👤 Pagó: {pagador}\n"
    if metodo:
        resumen += f"🏦 Método: {metodo}\n"
    resumen += "💸 Deudores:\n"
    for d in deudores:
        unidades = 2 if d in ["Bichos", "Fabos"] else 1
        resumen += f"• {d} paga ${monto_por_persona * unidades:,.2f}\n"

    keyboard = [
        [InlineKeyboardButton("Confirmar ✅", callback_data="confirmar")],
        [InlineKeyboardButton("Cancelar ❌", callback_data="cancelar")],
    ]
    await context.bot.send_message(chat_id=update.effective_chat.id, text=resumen, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRMACION

# Confirmamos y guardamos el gasto en Google Sheets
async def confirmar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    sheet = init_gsheet()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    descripcion = context.user_data.get("descripcion","")
    monto = context.user_data.get("monto",0)
    pagador = context.user_data.get("pagador","")
    metodo = context.user_data.get("metodo_pago","")
    deudores = context.user_data.get("deudores",[])
    total_personas = sum(2 if d in ["Bichos", "Fabos"] else 1 for d in deudores) or 1
    monto_por_persona = round(monto / total_personas, 2)

    for d in deudores:
        unidades = 2 if d in ["Bichos", "Fabos"] else 1
        row = [descripcion, monto_por_persona * unidades, d, pagador, now]
        if pagador == "Óscar":
            row.append(metodo)
        sheet.append_row(row)

    await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Gasto registrado exitosamente! ✅")
    return ConversationHandler.END