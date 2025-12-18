# bot.py
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from config import TOKEN, DESCRIPCION, MONTO, PAGADOR, DEUDORES, NOMBRE_DEUDOR_EXTRA, INCLUIR_PAGADOR, METODO_PAGO, CONFIRMACION, NOMBRE_PAGADOR_MANUAL, PAGAR_PAGADOR, PAGAR_RECEPTOR, PAGAR_MONTO, PAGAR_CONFIRMAR, PAGAR_PAGADOR_OTRO, PAGAR_RECEPTOR_OTRO

from handlers.start import start
from handlers.cancelar import cancelar
from handlers.saldo import saldo
from handlers.gasto import (
    gasto, recibir_descripcion, recibir_monto, recibir_pagador, 
    recibir_pagador_manual, recibir_deudores, agregar_deudor_manual,
    incluir_pagador, recibir_metodo_pago, confirmar_gasto
)
from handlers.pago import (
    pagar,
    pagar_pagador,
    pagar_pagador_otro,
    pagar_receptor,
    pagar_receptor_otro,
    pagar_monto,
    pagar_confirmar,
    pagar_cancelar,
)

logging.basicConfig(level=logging.INFO)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    gasto_handler = ConversationHandler(
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
            CONFIRMACION: [
                CallbackQueryHandler(confirmar_gasto, pattern="^confirmar$"),
                CallbackQueryHandler(cancelar, pattern="^cancelar$")
            ]
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )

    pago_handler = ConversationHandler(
        entry_points=[CommandHandler("pago", pagar)],
        states={
            PAGAR_PAGADOR: [CallbackQueryHandler(pagar_pagador)],
            PAGAR_PAGADOR_OTRO: [MessageHandler(filters.TEXT & ~filters.COMMAND, pagar_pagador_otro)],
            PAGAR_RECEPTOR: [CallbackQueryHandler(pagar_receptor)],
            PAGAR_RECEPTOR_OTRO: [MessageHandler(filters.TEXT & ~filters.COMMAND, pagar_receptor_otro)],
            PAGAR_MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, pagar_monto)],
            PAGAR_CONFIRMAR: [
                CallbackQueryHandler(pagar_confirmar, pattern="^confirmar_pago$"),
                CallbackQueryHandler(pagar_cancelar, pattern="^cancelar_pago$")
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(gasto_handler)
    app.add_handler(pago_handler)
    app.add_handler(CommandHandler("saldo", saldo))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancelar", cancelar))

    print("Bot corriendo…")
    app.run_polling()

if __name__ == "__main__":
    main()
