from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import (
    OPCIONES_PAGADORES,
    PAGAR_PAGADOR, PAGAR_RECEPTOR, PAGAR_MONTO, PAGAR_CONFIRMAR, PAGAR_PAGADOR_OTRO, PAGAR_RECEPTOR_OTRO
)
import datetime
from handlers.callback_guard import (
    finish_callback,
    mark_callback_processed,
    was_callback_processed,
)
from repositories.sheets_repository import append_movement
from services.finance_service import build_payment_row, build_payment_summary, generate_movement_id, parse_amount

async def pagar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

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

    if pagador == "Otro":
        await query.edit_message_text("✍️ Escribe el nombre del pagador:")
        return PAGAR_PAGADOR_OTRO

    context.user_data["pagador"] = pagador

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
    pagador = update.message.text
    context.user_data["pagador"] = pagador

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

    if receptor == "Otro":
        await query.edit_message_text("✍️ Escribe el nombre del receptor del pago:")
        return PAGAR_RECEPTOR_OTRO

    context.user_data["receptor"] = receptor

    await query.edit_message_text(
        f"💰 ¿Cuánto pagó *{context.user_data['pagador']}* a *{receptor}*?",
        parse_mode="Markdown"
    )
    return PAGAR_MONTO

async def pagar_receptor_otro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    receptor = update.message.text
    context.user_data["receptor"] = receptor

    await update.message.reply_text(
        f"💰 ¿Cuánto pagó *{context.user_data['pagador']}* a *{receptor}*?",
        parse_mode="Markdown"
    )
    return PAGAR_MONTO

async def pagar_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = parse_amount(update.message.text)
    except ValueError:
        await update.message.reply_text("Monto inválido. Escribe un número. Ej: 250.00")
        return PAGAR_MONTO

    context.user_data["monto"] = monto

    pagador = context.user_data["pagador"]
    receptor = context.user_data["receptor"]
    context.user_data.setdefault("pago_movement_id", generate_movement_id())

    resumen = build_payment_summary(pagador, receptor, monto)

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

    if was_callback_processed(context, "pago_confirmado"):
        await finish_callback(query, "⚠️ Este pago ya fue registrado anteriormente.")
        return ConversationHandler.END

    mark_callback_processed(context, "pago_confirmado")

    pagador = context.user_data["pagador"]
    receptor = context.user_data["receptor"]
    monto = context.user_data["monto"]

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    append_movement(
        build_payment_row(
            pagador,
            receptor,
            monto,
            timestamp,
            context.user_data.setdefault("pago_movement_id", generate_movement_id()),
        )
    )
    await finish_callback(query, "✅ Pago registrado. Esta confirmación ya quedó cerrada.")

    await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Pago registrado exitosamente! ✅")
    return ConversationHandler.END


async def pagar_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Operación cancelada.")
    return ConversationHandler.END
