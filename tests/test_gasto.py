import asyncio
import unittest
from unittest.mock import patch

from tests.helpers import FakeBot, FakeCallbackQuery, FakeContext, FakeSheet, FakeUpdate

from config import CONFIRMACION
from handlers.gasto import confirmar_gasto, mostrar_confirmacion
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
        sheet = FakeSheet()
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

        with patch("handlers.gasto.init_gsheet", return_value=sheet):
            state = asyncio.run(confirmar_gasto(update, context))

        self.assertEqual(state, ConversationHandler.END)
        self.assertEqual(len(sheet.rows), 2)
        self.assertEqual(sheet.rows[0][0], "Super")
        self.assertEqual(sheet.rows[0][1], 100.0)
        self.assertEqual(sheet.rows[0][2], "Yetro")
        self.assertEqual(sheet.rows[0][3], "Óscar")
        self.assertEqual(sheet.rows[0][-1], "Tarjeta")
        self.assertEqual(sheet.rows[1][1], 200.0)
        self.assertEqual(sheet.rows[1][2], "Fabos")
        self.assertEqual(context.bot.sent_messages[0]["text"], "¡Gasto registrado exitosamente! ✅")
