import asyncio
import unittest
from unittest.mock import patch

from domain.errors import RepositoryError
from domain.models import ExpenseDraft, Movement
from tests.helpers import FakeBot, FakeCallbackQuery, FakeContext, FakeUpdate

from config import CONFIRMACION, DEUDORES, NOMBRE_DEUDOR_EXTRA, NOMBRE_PAGADOR_MANUAL
from handlers.gasto import (
    confirmar_gasto,
    mostrar_confirmacion,
    recibir_deudores,
    recibir_pagador,
    recibir_pagador_manual,
)
from services.finance_service import build_expense_rows
from telegram.ext import ConversationHandler


class GastoTests(unittest.TestCase):
    def test_recibir_pagador_otro_no_duplica_mensaje(self):
        bot = FakeBot()
        update = FakeUpdate(callback_query=FakeCallbackQuery("Otro"))
        context = FakeContext(
            bot=bot,
            user_data={"expense_draft": ExpenseDraft()},
        )

        state = asyncio.run(recibir_pagador(update, context))

        self.assertEqual(state, NOMBRE_PAGADOR_MANUAL)
        self.assertEqual(update.callback_query.edits[0]["text"], "✅ Opción manual seleccionada.")
        self.assertEqual(len(bot.sent_messages), 1)
        self.assertEqual(bot.sent_messages[0]["text"], "✍️ Escribe el *nombre del pagador*.")

    def test_recibir_pagador_cierra_mensaje_viejo_y_avanza(self):
        bot = FakeBot()
        update = FakeUpdate(callback_query=FakeCallbackQuery("Óscar"))
        context = FakeContext(
            bot=bot,
            user_data={"expense_draft": ExpenseDraft()},
        )

        state = asyncio.run(recibir_pagador(update, context))

        self.assertEqual(state, DEUDORES)
        self.assertEqual(update.callback_query.edits[0]["text"], "✅ Pagó: *Óscar*")
        self.assertEqual(bot.sent_messages[0]["text"], "💸 ¿*Quiénes deben pagar* este gasto?")

    def test_recibir_pagador_manual_no_muestra_listo_sin_deudores(self):
        bot = FakeBot()
        update = FakeUpdate(message=type("Msg", (), {"text": "Carlos", "reply_text": None})())
        context = FakeContext(
            bot=bot,
            user_data={"expense_draft": ExpenseDraft()},
        )

        async def fake_reply_text(text, **kwargs):
            bot.sent_messages.append({"text": text, **kwargs})

        update.message.reply_text = fake_reply_text

        state = asyncio.run(recibir_pagador_manual(update, context))

        self.assertEqual(state, DEUDORES)
        keyboard = bot.sent_messages[0]["reply_markup"].keyboard
        labels = [button.text for row in keyboard for button in row]
        self.assertNotIn("Listo", labels)

    def test_recibir_deudores_otro_no_duplica_mensaje(self):
        bot = FakeBot()
        update = FakeUpdate(callback_query=FakeCallbackQuery("Otro"))
        context = FakeContext(
            bot=bot,
            user_data={"expense_draft": ExpenseDraft(pagador="Óscar")},
        )

        state = asyncio.run(recibir_deudores(update, context))

        self.assertEqual(state, NOMBRE_DEUDOR_EXTRA)
        self.assertEqual(update.callback_query.edits[0]["text"], "✅ Opción manual seleccionada.")
        self.assertEqual(len(bot.sent_messages), 1)
        self.assertEqual(bot.sent_messages[0]["text"], "✍️ Escribe el *nombre del otro deudor*.")

    def test_mostrar_confirmacion_reparte_por_pesos(self):
        bot = FakeBot()
        context = FakeContext(
            bot=bot,
            user_data={
                "expense_draft": ExpenseDraft(
                    descripcion="Cena",
                    monto=300.0,
                    pagador="Óscar",
                    deudores=["Yetro", "Fabos"],
                    metodo_pago="Tarjeta",
                ),
            },
        )

        state = asyncio.run(mostrar_confirmacion(FakeUpdate(), context))

        self.assertEqual(state, CONFIRMACION)
        self.assertEqual(len(bot.sent_messages), 1)
        resumen = bot.sent_messages[0]["text"]
        self.assertIn("📌 *Cena*", resumen)
        self.assertIn("Yetro paga $100.00", resumen)
        self.assertIn("Fabos paga $200.00", resumen)
        self.assertEqual(bot.sent_messages[0]["parse_mode"], "Markdown")

    def test_confirmar_gasto_guarda_una_fila_por_deudor(self):
        update = FakeUpdate(callback_query=FakeCallbackQuery("confirmar"))
        context = FakeContext(
            user_data={
                "expense_draft": ExpenseDraft(
                    descripcion="Super",
                    monto=300.0,
                    pagador="Óscar",
                    deudores=["Yetro", "Fabos"],
                    metodo_pago="Tarjeta",
                    movement_id="gasto-123",
                ),
            }
        )

        with patch("handlers.gasto.append_movements") as mocked_append_movements:
            state = asyncio.run(confirmar_gasto(update, context))

        self.assertEqual(state, ConversationHandler.END)
        movements = mocked_append_movements.call_args.args[0]
        self.assertEqual(len(movements), 2)
        self.assertEqual(movements[0].descripcion, "Super")
        self.assertEqual(movements[0].monto, 100.0)
        self.assertEqual(movements[0].deudor, "Yetro")
        self.assertEqual(movements[0].acreedor, "Óscar")
        self.assertEqual(movements[0].metodo_pago, "Tarjeta")
        self.assertEqual(movements[0].movement_id, "gasto-123")
        self.assertEqual(movements[0].movement_id, movements[1].movement_id)
        self.assertEqual(movements[1].monto, 200.0)
        self.assertEqual(movements[1].deudor, "Fabos")
        self.assertEqual(context.bot.sent_messages[0]["text"], "✅ *Gasto registrado correctamente.*")
        self.assertEqual(
            update.callback_query.edits[0]["text"],
            "✅ *Confirmación cerrada.*",
        )

    def test_confirmar_gasto_no_registra_dos_veces(self):
        update = FakeUpdate(callback_query=FakeCallbackQuery("confirmar"))
        context = FakeContext(
            user_data={
                "expense_draft": ExpenseDraft(
                    descripcion="Super",
                    monto=300.0,
                    pagador="Óscar",
                    deudores=["Yetro", "Fabos"],
                    metodo_pago="Tarjeta",
                    movement_id="gasto-123",
                ),
            }
        )

        with patch("handlers.gasto.append_movements") as mocked_append_movements:
            first_state = asyncio.run(confirmar_gasto(update, context))
            second_state = asyncio.run(confirmar_gasto(update, context))

        self.assertEqual(first_state, ConversationHandler.END)
        self.assertEqual(second_state, ConversationHandler.END)
        self.assertEqual(mocked_append_movements.call_count, 1)
        self.assertEqual(
            update.callback_query.edits[-1]["text"],
            "⚠️ Este gasto *ya había sido registrado*.",
        )

    def test_confirmar_gasto_muestra_error_si_falla_persistencia(self):
        update = FakeUpdate(callback_query=FakeCallbackQuery("confirmar"))
        draft = ExpenseDraft(
            descripcion="Super",
            monto=300.0,
            pagador="Óscar",
            deudores=["Yetro", "Fabos"],
            metodo_pago="Tarjeta",
            movement_id="gasto-123",
        )
        context = FakeContext(user_data={"expense_draft": draft})

        with patch("handlers.gasto.append_movements", side_effect=RepositoryError("fallo")):
            state = asyncio.run(confirmar_gasto(update, context))

        self.assertEqual(state, CONFIRMACION)
        self.assertFalse(draft.processed)
        self.assertEqual(
            update.callback_query.edits[-1]["text"],
            "❌ No pude guardar el gasto en este momento.\n\nIntenta de nuevo en unos minutos.",
        )

    def test_build_expense_rows_reparte_por_pesos(self):
        movements = build_expense_rows(
            "Cena",
            300.0,
            "Óscar",
            ["Yetro", "Fabos"],
            "2026-03-23 10:00:00",
            "Tarjeta",
        )

        self.assertEqual(
            movements,
            [
                Movement("Cena", 100.0, "Yetro", "Óscar", "2026-03-23 10:00:00", "Tarjeta", ""),
                Movement("Cena", 200.0, "Fabos", "Óscar", "2026-03-23 10:00:00", "Tarjeta", ""),
            ],
        )
