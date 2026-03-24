import asyncio
import unittest
from unittest.mock import patch

from domain.models import Movement
from tests.helpers import FakeBot, FakeCallbackQuery, FakeContext, FakeUpdate

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
        self.assertEqual(movements[1].monto, 200.0)
        self.assertEqual(movements[1].deudor, "Fabos")
        self.assertEqual(context.bot.sent_messages[0]["text"], "¡Gasto registrado exitosamente! ✅")

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
                Movement("Cena", 100.0, "Yetro", "Óscar", "2026-03-23 10:00:00", "Tarjeta"),
                Movement("Cena", 200.0, "Fabos", "Óscar", "2026-03-23 10:00:00", "Tarjeta"),
            ],
        )
