from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import datetime
from config import (
    DESCRIPCION, MONTO, PAGADOR, DEUDORES, NOMBRE_DEUDOR_EXTRA,
    INCLUIR_PAGADOR, METODO_PAGO, CONFIRMACION, NOMBRE_PAGADOR_MANUAL,
    OPCIONES_PAGADORES, METODOS
)
from domain.errors import RepositoryError
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
)
from services.validators import is_expected_reply, validate_amount_text, validate_required_name

# Al invocar el comando de /gasto
# Preguntamos por la descripción del gasto
async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = create_expense_draft(context)
    mensaje = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🧾 *Nuevo gasto*\n\nCuéntame la *descripción del gasto*.\nRespóndeme directamente a este mensaje.",
        parse_mode="Markdown"
    )
    draft.mensaje_descripcion_id = mensaje.message_id
    return DESCRIPCION

# Recibimos descripción del mensaje y preguntamos por monto que fue gastado
async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_expense_draft(context)
    if not is_expected_reply(update.message, draft.mensaje_descripcion_id):
        await update.message.reply_text("⚠️ Respóndeme directamente al mensaje donde te pedí la *descripción del gasto*.", parse_mode="Markdown")
        return DESCRIPCION

    draft.descripcion = update.message.text
    mensaje_monto = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="💰 Ahora dime el *monto total*.\n\nEjemplo: *1234.56*\nRespóndeme directamente a este mensaje.",
        parse_mode="Markdown"
    )
    draft.mensaje_monto_id = mensaje_monto.message_id
    return MONTO

# Recibimos monto y preguntamos por pagador
async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_expense_draft(context)
    if not is_expected_reply(update.message, draft.mensaje_monto_id):
        await update.message.reply_text("⚠️ Respóndeme directamente al mensaje donde te pedí el *monto total*.", parse_mode="Markdown")
        return MONTO

    try:
        draft.monto = validate_amount_text(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ No entendí ese monto.\n\nEscríbelo como número, por ejemplo: *250.00*", parse_mode="Markdown")
        return MONTO

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👤 ¿*Quién pagó* este gasto?",
        parse_mode="Markdown",
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
        await finish_callback(query, "✅ Opción manual seleccionada.")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✍️ Escribe el *nombre del pagador*.", parse_mode="Markdown")
        return NOMBRE_PAGADOR_MANUAL
    else:
        draft.pagador = opcion
        draft.deudores.clear()
        draft.primer_pregunta_deudores = True
        await finish_callback(query, f"✅ Pagó: *{opcion}*")

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="💸 ¿*Quiénes deben pagar* este gasto?",
            parse_mode="Markdown",
            reply_markup=build_deudores_keyboard(opcion, [], show_done=False),
        )

        return DEUDORES
# Recibimos deudor manual y preguntamos por deudores
async def recibir_pagador_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_expense_draft(context)
    try:
        pagador = validate_required_name(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Ese nombre no me sirve.\n\nEscríbelo de nuevo, por favor.")
        return NOMBRE_PAGADOR_MANUAL

    draft.pagador = pagador
    draft.deudores.clear()
    draft.primer_pregunta_deudores = False

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"👤 Pagador registrado: *{pagador}*\n\n💸 ¿*Quiénes deben pagar* este gasto?",
        parse_mode="Markdown",
        reply_markup=build_deudores_keyboard(pagador, [], show_done=False),
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
        await finish_callback(query, "✅ *Selección de deudores cerrada.*")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🤔 ¿El *pagador* también entra en la división?",
            parse_mode="Markdown",
            reply_markup=build_include_pagador_keyboard(),
        )
        return INCLUIR_PAGADOR

    elif data == "Los 4 de siempre":
        grupo_final = build_fixed_group(pagador)
        draft.add_deudores(grupo_final)
        mensaje = f"✅ Se agregaron: *{', '.join(grupo_final)}*\n\n"
        await finish_callback(query, f"✅ Deudores agregados: *{', '.join(grupo_final)}*")

    elif data == "Otro":
        await finish_callback(query, "✅ Opción manual seleccionada.")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✍️ Escribe el *nombre del otro deudor*.", parse_mode="Markdown")
        return NOMBRE_DEUDOR_EXTRA

    else:
        if draft.add_deudor(data):
            mensaje = f"✅ *{data}* fue agregado como deudor.\n\n"
            await finish_callback(query, f"✅ Deudor agregado: *{data}*")
        else:
            mensaje = f"⚠️ *{data}* ya fue agregado o es el pagador.\n\n"
            await finish_callback(query, f"⚠️ *{data}* ya estaba agregado o es el pagador.")

    mensaje += "Puedes seguir eligiendo deudores o tocar *Listo* para continuar."
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
    try:
        nuevo = validate_required_name(update.message.text)
        if draft.add_deudor(nuevo):
            mensaje = f"✅ *{nuevo}* fue agregado como deudor.\n\n"
        else:
            mensaje = f"⚠️ *{nuevo}* ya está en la lista de deudores.\n\n"
    except ValueError:
        mensaje = "❌ Ese nombre no me sirve.\n\n"

    mensaje += "Puedes seguir eligiendo deudores o tocar *Listo* para continuar."

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
        await finish_callback(query, "✅ El pagador *sí* fue incluido en la división.")
    else:
        await finish_callback(query, "✅ El pagador *no* fue incluido en la división.")

    if should_ask_payment_method(pagador):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🏦 ¿Con qué *método de pago* pagó *Óscar*?",
            parse_mode="Markdown",
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
    await finish_callback(query, f"✅ Método de pago: *{query.data}*")
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
    resumen = resumen.replace("📌", "🧾 *Resumen del gasto*\n\n📌", 1)
    resumen += "\n¿Quieres *registrar* este gasto?"

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
        await finish_callback(query, "⚠️ Este gasto *ya había sido registrado*.")
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
    try:
        append_movements(movements)
    except RepositoryError:
        draft.processed = False
        await finish_callback(query, "❌ No pude guardar el gasto en este momento.\n\nIntenta de nuevo en unos minutos.")
        return CONFIRMACION

    await finish_callback(query, "✅ *Confirmación cerrada.*")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ *Gasto registrado correctamente.*",
        parse_mode="Markdown",
    )
    return ConversationHandler.END
