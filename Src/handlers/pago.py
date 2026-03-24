from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import (
    OPCIONES_PAGADORES,
    PAGAR_PAGADOR, PAGAR_RECEPTOR, PAGAR_DECISION_MONTO, PAGAR_MONTO, PAGAR_CONFIRMAR, PAGAR_PAGADOR_OTRO, PAGAR_RECEPTOR_OTRO
)
import datetime
from domain.errors import RepositoryError
from handlers.callback_guard import finish_callback
from handlers.conversation_state import create_payment_draft, get_payment_draft
from repositories.sheets_repository import append_movement, fetch_movements
from services.finance_service import (
    build_payment_row,
    build_payment_summary,
    generate_movement_id,
    get_creditors_for_debtor,
    get_debt_amount,
    get_people_with_debt,
)
from services.validators import validate_amount_text, validate_required_name

async def pagar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    create_payment_draft(context)
    try:
        movements = fetch_movements()
        opciones = get_people_with_debt(movements)
    except RepositoryError:
        await update.message.reply_text("❌ No pude consultar las deudas en este momento. Intenta de nuevo más tarde.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in opciones + ["Otro"]]

    await update.message.reply_text(
        "💸 ¿Quién está pagando? Te muestro primero quienes tienen deudas registradas.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PAGAR_PAGADOR

async def pagar_pagador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pagador = query.data
    draft = get_payment_draft(context)

    if pagador == "Otro":
        await query.edit_message_text("✍️ Escribe el nombre del pagador:")
        return PAGAR_PAGADOR_OTRO

    draft.pagador = pagador

    try:
        movimientos = fetch_movements()
        opciones = get_creditors_for_debtor(movimientos, pagador)
    except RepositoryError:
        await query.edit_message_text("❌ No pude consultar a quién le debe en este momento.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in opciones + ["Otro"]]

    await query.edit_message_text(
        f"💳 ¿A quién le está pagando *{pagador}*? Te muestro primero a quienes les debe.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PAGAR_RECEPTOR

async def pagar_pagador_otro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_payment_draft(context)
    try:
        pagador = validate_required_name(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Nombre no válido. Intenta nuevamente.")
        return PAGAR_PAGADOR_OTRO
    draft.pagador = pagador

    try:
        movimientos = fetch_movements()
        opciones = get_creditors_for_debtor(movimientos, pagador)
    except RepositoryError:
        await update.message.reply_text("❌ No pude consultar a quién le debe en este momento.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in opciones + ["Otro"]]

    await update.message.reply_text(
        f"💳 ¿A quién le está pagando *{pagador}*?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PAGAR_RECEPTOR

async def pagar_receptor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    receptor = query.data
    draft = get_payment_draft(context)

    if receptor == "Otro":
        await query.edit_message_text("✍️ Escribe el nombre del receptor del pago:")
        return PAGAR_RECEPTOR_OTRO

    draft.receptor = receptor
    try:
        movimientos = fetch_movements()
        draft.deuda_sugerida = get_debt_amount(movimientos, draft.pagador, receptor)
    except RepositoryError:
        await query.edit_message_text("❌ No pude consultar el saldo de esta deuda en este momento.")
        return ConversationHandler.END

    if draft.deuda_sugerida > 0:
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(f"Liquidar deuda (${draft.deuda_sugerida:,.2f})", callback_data="liquidar_deuda")],
                [InlineKeyboardButton("Otro monto", callback_data="otro_monto")],
            ]
        )
        await query.edit_message_text(
            f"💰 *{draft.pagador}* le debe a *{receptor}* un total de ${draft.deuda_sugerida:,.2f}.\n\n¿Qué quieres hacer?",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return PAGAR_DECISION_MONTO

    await query.edit_message_text(
        f"💰 ¿Cuánto pagó *{draft.pagador}* a *{receptor}*?",
        parse_mode="Markdown"
    )
    return PAGAR_MONTO

async def pagar_receptor_otro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_payment_draft(context)
    try:
        receptor = validate_required_name(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Nombre no válido. Intenta nuevamente.")
        return PAGAR_RECEPTOR_OTRO
    draft.receptor = receptor
    draft.deuda_sugerida = 0.0

    await update.message.reply_text(
        f"💰 ¿Cuánto pagó *{draft.pagador}* a *{receptor}*?",
        parse_mode="Markdown"
    )
    return PAGAR_MONTO


async def pagar_decidir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    draft = get_payment_draft(context)

    if query.data == "liquidar_deuda":
        draft.monto = draft.deuda_sugerida
        if not draft.movement_id:
            draft.movement_id = generate_movement_id()

        resumen = build_payment_summary(draft.pagador, draft.receptor, draft.monto)
        keyboard = [
            [InlineKeyboardButton("Confirmar ✅", callback_data="confirmar_pago")],
            [InlineKeyboardButton("Cancelar ❌", callback_data="cancelar_pago")],
        ]
        await query.edit_message_text(
            resumen,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return PAGAR_CONFIRMAR

    await query.edit_message_text(
        f"💰 ¿Cuánto pagó *{draft.pagador}* a *{draft.receptor}*?",
        parse_mode="Markdown",
    )
    return PAGAR_MONTO

async def pagar_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_payment_draft(context)
    try:
        monto = validate_amount_text(update.message.text)
    except ValueError:
        await update.message.reply_text("Monto inválido. Escribe un número. Ej: 250.00")
        return PAGAR_MONTO

    draft.monto = monto
    if not draft.movement_id:
        draft.movement_id = generate_movement_id()

    resumen = build_payment_summary(draft.pagador, draft.receptor, monto)

    keyboard = [
        [InlineKeyboardButton("Confirmar ✅", callback_data="confirmar_pago")],
        [InlineKeyboardButton("Cancelar ❌", callback_data="cancelar_pago")],
    ]

    await update.message.reply_text(
        resumen,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return PAGAR_CONFIRMAR


async def pagar_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    draft = get_payment_draft(context)

    if draft.processed:
        await finish_callback(query, "⚠️ Este pago ya fue registrado anteriormente.")
        return ConversationHandler.END

    draft.processed = True

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        append_movement(
            build_payment_row(
                draft.pagador,
                draft.receptor,
                draft.monto,
                timestamp,
                draft.movement_id or generate_movement_id(),
            )
        )
    except RepositoryError:
        draft.processed = False
        await finish_callback(query, "❌ No pude registrar el pago. Intenta de nuevo en unos minutos.")
        return PAGAR_CONFIRMAR
    await finish_callback(query, "✅ Pago registrado. Esta confirmación ya quedó cerrada.")

    await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Pago registrado exitosamente! ✅")
    return ConversationHandler.END


async def pagar_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Operación cancelada.")
    return ConversationHandler.END
