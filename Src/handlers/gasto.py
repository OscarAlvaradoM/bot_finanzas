from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import datetime
from config import (
    DESCRIPCION, MONTO, PAGADOR, DEUDORES, NOMBRE_DEUDOR_EXTRA,
    INCLUIR_PAGADOR, METODO_PAGO, CONFIRMACION, NOMBRE_PAGADOR_MANUAL,
    OPCIONES_PAGADORES, METODOS
)
from handlers.gasto_ui import (
    build_deudores_keyboard,
    build_include_pagador_keyboard,
    build_name_keyboard,
    build_payment_method_keyboard,
    should_ask_payment_method,
)
from repositories.sheets_repository import append_movements
from services.finance_service import (
    build_expense_rows,
    build_expense_summary,
    build_fixed_group,
    parse_amount,
)

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
        context.user_data["monto"] = parse_amount(update.message.text)
    except ValueError:
        await update.message.reply_text("Por favor, escribe un monto válido (ej. 250.00)")
        return MONTO

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👤 ¿Quién pagó?",
        reply_markup=build_name_keyboard(OPCIONES_PAGADORES, include_other=True),
    )
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

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="💸 ¿Quiénes deben pagar?",
            reply_markup=build_deudores_keyboard(opcion, [], show_done=False),
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

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"👤 Nuevo pagador registrado: *{pagador}*\n\n💸 ¿Quiénes deben pagar?",
        parse_mode="Markdown",
        reply_markup=build_deudores_keyboard(pagador, [], show_done=True),
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
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="¿El pagador también es deudor?",
            reply_markup=build_include_pagador_keyboard(),
        )
        return INCLUIR_PAGADOR

    elif data == "Los 4 de siempre":
        grupo_final = build_fixed_group(pagador)
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

    mensaje += "Sigue eligiendo deudores o presiona *Listo* para continuar."
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=mensaje,
        parse_mode="Markdown",
        reply_markup=build_deudores_keyboard(
            pagador,
            context.user_data.get("deudores", []),
            show_done=not context.user_data.get("primer_pregunta_deudores", True),
        ),
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

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=mensaje,
        parse_mode="Markdown",
        reply_markup=build_deudores_keyboard(
            context.user_data["pagador"],
            context.user_data.get("deudores", []),
            show_done=True,
        ),
    )
    return DEUDORES

# Recibinmos respuesta de si pagador es deudor y preguntamos por método de pago (en caso de ser Óscar) o confirmación
async def incluir_pagador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pagador = context.user_data["pagador"]
    if query.data == "si" and pagador not in context.user_data.get("deudores", []):
        context.user_data.setdefault("deudores", []).append(pagador)

    if should_ask_payment_method(pagador):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🏦 ¿Con qué método pagó Óscar?",
            reply_markup=build_payment_method_keyboard(METODOS),
        )
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
    descripcion = context.user_data.get("descripcion", "")
    monto = context.user_data.get("monto", 0)
    pagador = context.user_data.get("pagador", "")
    deudores = context.user_data.get("deudores", [])
    metodo = context.user_data.get("metodo_pago")
    resumen = build_expense_summary(descripcion, monto, pagador, deudores, metodo)

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

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    movements = build_expense_rows(
        context.user_data.get("descripcion", ""),
        context.user_data.get("monto", 0),
        context.user_data.get("pagador", ""),
        context.user_data.get("deudores", []),
        now,
        context.user_data.get("metodo_pago", ""),
    )
    append_movements(movements)

    await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Gasto registrado exitosamente! ✅")
    return ConversationHandler.END
