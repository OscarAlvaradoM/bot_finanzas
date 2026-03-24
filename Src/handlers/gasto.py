from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import datetime
from config import (
    DESCRIPCION, MONTO, PAGADOR, DEUDORES, NOMBRE_DEUDOR_EXTRA,
    INCLUIR_PAGADOR, METODO_PAGO, CONFIRMACION, NOMBRE_PAGADOR_MANUAL,
    OPCIONES_PAGADORES, METODOS
)
from handlers.callback_guard import (
    finish_callback,
)
from handlers.conversation_state import (
    create_expense_draft,
    get_expense_draft,
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
    generate_movement_id,
    parse_amount,
)

# Al invocar el comando de /gasto
# Preguntamos por la descripción del gasto
async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = create_expense_draft(context)
    mensaje = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="📌 ¿Cuál es la descripción del gasto?\n\nResponde directamente a este mensaje.",
        parse_mode="Markdown"
    )
    draft.mensaje_descripcion_id = mensaje.message_id
    return DESCRIPCION

# Recibimos descripción del mensaje y preguntamos por monto que fue gastado
async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_expense_draft(context)
    mensaje_esperado = draft.mensaje_descripcion_id
    if update.message.reply_to_message and update.message.reply_to_message.message_id != mensaje_esperado:
        await update.message.reply_text("Por favor, responde directamente al mensaje que pregunta por la descripción del gasto.")
        return DESCRIPCION

    draft.descripcion = update.message.text
    mensaje_monto = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="💰 ¿Cuál fue el monto total? (ej. 1234.56)\n\nResponde directamente a este mensaje.",
        parse_mode="Markdown"
    )
    draft.mensaje_monto_id = mensaje_monto.message_id
    return MONTO

# Recibimos monto y preguntamos por pagador
async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_expense_draft(context)
    mensaje_esperado = draft.mensaje_monto_id
    if update.message.reply_to_message and update.message.reply_to_message.message_id != mensaje_esperado:
        await update.message.reply_text("Por favor, responde directamente al mensaje que pregunta por el monto.")
        return MONTO

    try:
        draft.monto = parse_amount(update.message.text)
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
    draft = get_expense_draft(context)

    if opcion == "Otro":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✍️ Escribe el nombre del pagador:")
        return NOMBRE_PAGADOR_MANUAL
    else:
        draft.pagador = opcion
        draft.deudores.clear()
        draft.primer_pregunta_deudores = True

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="💸 ¿Quiénes deben pagar?",
            reply_markup=build_deudores_keyboard(opcion, [], show_done=False),
        )

        return DEUDORES
# Recibimos deudor manual y preguntamos por deudores
async def recibir_pagador_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_expense_draft(context)
    pagador = update.message.text.strip()
    if not pagador:
        await update.message.reply_text("❌ Nombre no válido. Intenta nuevamente.")
        return NOMBRE_PAGADOR_MANUAL

    draft.pagador = pagador
    draft.deudores.clear()
    draft.primer_pregunta_deudores = False

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
    draft = get_expense_draft(context)
    pagador = draft.pagador
    deudores = draft.deudores

    if data == "Listo":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="¿El pagador también es deudor?",
            reply_markup=build_include_pagador_keyboard(),
        )
        return INCLUIR_PAGADOR

    elif data == "Los 4 de siempre":
        grupo_final = build_fixed_group(pagador)
        draft.add_deudores(grupo_final)
        mensaje = f"✅ Se agregaron: {', '.join(grupo_final)}\n\n"

    elif data == "Otro":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✍️ Escribe el nombre del otro deudor:")
        return NOMBRE_DEUDOR_EXTRA

    else:
        if draft.add_deudor(data):
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
            draft.deudores,
            show_done=not draft.primer_pregunta_deudores,
        ),
    )
    return DEUDORES

# Recibimos deudor extra manualmente y volvemos a preguntar por deudores
async def agregar_deudor_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_expense_draft(context)
    nuevo = update.message.text.strip()
    if nuevo:
        if draft.add_deudor(nuevo):
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
            draft.pagador,
            draft.deudores,
            show_done=True,
        ),
    )
    return DEUDORES

# Recibinmos respuesta de si pagador es deudor y preguntamos por método de pago (en caso de ser Óscar) o confirmación
async def incluir_pagador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    draft = get_expense_draft(context)
    pagador = draft.pagador
    if query.data == "si":
        draft.include_pagador()

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
    draft = get_expense_draft(context)
    draft.metodo_pago = query.data
    return await mostrar_confirmacion(update, context)

# Mostramos el resumen del gasto y pedimos confirmación o cancelación
async def mostrar_confirmacion(update, context):
    draft = get_expense_draft(context)
    if not draft.movement_id:
        draft.movement_id = generate_movement_id()
    resumen = build_expense_summary(
        draft.descripcion,
        draft.monto,
        draft.pagador,
        draft.deudores,
        draft.metodo_pago or None,
    )

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
    draft = get_expense_draft(context)

    if draft.processed:
        await finish_callback(query, "⚠️ Este gasto ya fue registrado anteriormente.")
        return ConversationHandler.END

    draft.processed = True

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    movements = build_expense_rows(
        draft.descripcion,
        draft.monto,
        draft.pagador,
        draft.deudores,
        now,
        draft.metodo_pago,
        draft.movement_id or generate_movement_id(),
    )
    append_movements(movements)
    await finish_callback(query, "✅ Gasto registrado. Esta confirmación ya quedó cerrada.")

    await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Gasto registrado exitosamente! ✅")
    return ConversationHandler.END
