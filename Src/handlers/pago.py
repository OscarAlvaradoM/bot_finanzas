from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import (
    OPCIONES_PAGADORES,
    PAGAR_PAGADOR, PAGAR_RECEPTOR, PAGAR_MONTO, PAGAR_CONFIRMAR
)
import datetime
from sheets import init_gsheet

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
        return PAGAR_PAGADOR

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


async def pagar_receptor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    receptor = query.data

    if receptor == "Otro":
        await query.edit_message_text("✍️ Escribe el nombre del receptor del pago:")
        return PAGAR_RECEPTOR

    context.user_data["receptor"] = receptor

    await query.edit_message_text(
        f"💰 ¿Cuánto pagó *{context.user_data['pagador']}* a *{receptor}*?",
        parse_mode="Markdown"
    )
    return PAGAR_MONTO


async def pagar_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(update.message.text.replace("$", "").replace(",", ""))
    except:
        await update.message.reply_text("Monto inválido. Escribe un número. Ej: 250.00")
        return PAGAR_MONTO

    context.user_data["monto"] = monto

    pagador = context.user_data["pagador"]
    receptor = context.user_data["receptor"]

    resumen = (
        "📌 *Confirmar pago*\n\n"
        f"👤 Pagador: {pagador}\n"
        f"➡️ Receptor: {receptor}\n"
        f"💵 Monto: ${monto:,.2f}\n\n"
        "¿Registrar este pago?"
    )

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

    sheet = init_gsheet()
    pagador = context.user_data["pagador"]
    receptor = context.user_data["receptor"]
    monto = context.user_data["monto"]

    # Insertar en Google Sheets como monto negativo
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    descripcion = "Pago"

    row = [
        descripcion,
        -monto,       # NEGATIVO
        pagador,     # Deudor = quien recibe el pago
        receptor,      # Prestador = quien paga
        timestamp,
        ""            # Método vacío
    ]
    sheet.append_row(row)

    await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Pago registrado exitosamente! ✅")
    return ConversationHandler.END


async def pagar_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Operación cancelada.")
    return ConversationHandler.END
