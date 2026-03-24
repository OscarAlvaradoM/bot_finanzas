from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import (
    OPCIONES_PAGADORES,
    PAGAR_PAGADOR, PAGAR_RECEPTOR, PAGAR_MONTO, PAGAR_CONFIRMAR, PAGAR_PAGADOR_OTRO, PAGAR_RECEPTOR_OTRO
)
import datetime
from domain.errors import RepositoryError
from handlers.callback_guard import finish_callback
from handlers.conversation_state import create_payment_draft, get_payment_draft
from repositories.sheets_repository import append_movement
from services.finance_service import build_payment_row, build_payment_summary, generate_movement_id
from services.validators import validate_amount_text, validate_required_name

async def pagar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    create_payment_draft(context)

    keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in OPCIONES_PAGADORES + ["Otro"]]

    await update.message.reply_text(
        "💸 ¿Quién está pagando?",
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

    # Preguntar a quién paga
    opciones = [p for p in OPCIONES_PAGADORES if p != pagador]
    keyboard = [[InlineKeyboardButton(n, callback_data=n)] for n in opciones + ["Otro"]]

    await query.edit_message_text(
        f"💳 ¿A quién le está pagando *{pagador}*?",
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

    opciones = [p for p in OPCIONES_PAGADORES if p != pagador]
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

    await update.message.reply_text(
        f"💰 ¿Cuánto pagó *{draft.pagador}* a *{receptor}*?",
        parse_mode="Markdown"
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
