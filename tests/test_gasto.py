import asyncio
import unittest
from unittest.mock import patch

from tests.helpers import FakeBot, FakeCallbackQuery, FakeContext, FakeSheet, FakeUpdate

from config import CONFIRMACION
from handlers.gasto import confirmar_gasto, mostrar_confirmacion
from services.finance_service import build_expense_rows
from telegram.ext import ConversationHandler


class GastoTests(unittest.TestCase):
    def test_mostrar_confirmacion_reparte_por_pesos(self):
        bot = FakeBot()
        context = FakeContext(
            bot=bot,
            user_data={
                "descripcion": "Cena",
                "monto": 300.0,
                "pagador": "Óscar",
                "deudores": ["Yetro", "Fabos"],
                "metodo_pago": "Tarjeta",
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
                "descripcion": "Super",
                "monto": 300.0,
                "pagador": "Óscar",
                "deudores": ["Yetro", "Fabos"],
                "metodo_pago": "Tarjeta",
            }
        )

        with patch("handlers.gasto.append_rows") as mocked_append_rows:
            state = asyncio.run(confirmar_gasto(update, context))

        self.assertEqual(state, ConversationHandler.END)
        rows = mocked_append_rows.call_args.args[0]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "Super")
        self.assertEqual(rows[0][1], 100.0)
        self.assertEqual(rows[0][2], "Yetro")
        self.assertEqual(rows[0][3], "Óscar")
        self.assertEqual(rows[0][-1], "Tarjeta")
        self.assertEqual(rows[1][1], 200.0)
        self.assertEqual(rows[1][2], "Fabos")
        self.assertEqual(context.bot.sent_messages[0]["text"], "¡Gasto registrado exitosamente! ✅")

    def test_build_expense_rows_reparte_por_pesos(self):
        rows = build_expense_rows(
            "Cena",
            300.0,
            "Óscar",
            ["Yetro", "Fabos"],
            "2026-03-23 10:00:00",
            "Tarjeta",
        )

        self.assertEqual(
            rows,
            [
                ["Cena", 100.0, "Yetro", "Óscar", "2026-03-23 10:00:00", "Tarjeta"],
                ["Cena", 200.0, "Fabos", "Óscar", "2026-03-23 10:00:00", "Tarjeta"],
            ],
        )
