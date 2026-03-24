import asyncio
import unittest
from unittest.mock import patch

from tests.helpers import FakeCallbackQuery, FakeContext, FakeSheet, FakeUpdate

from handlers.pago import pagar_confirmar
from telegram.ext import ConversationHandler


class PagoTests(unittest.TestCase):
    def test_pagar_confirmar_registra_monto_negativo(self):
        sheet = FakeSheet()
        update = FakeUpdate(callback_query=FakeCallbackQuery("confirmar_pago"))
        context = FakeContext(
            user_data={
                "pagador": "Óscar",
                "receptor": "Yetro",
                "monto": 250.0,
            }
        )

        with patch("handlers.pago.init_gsheet", return_value=sheet):
            state = asyncio.run(pagar_confirmar(update, context))

        self.assertEqual(state, ConversationHandler.END)
        self.assertEqual(len(sheet.rows), 1)
        row = sheet.rows[0]
        self.assertEqual(row[0], "Pago")
        self.assertEqual(row[1], -250.0)
        self.assertEqual(row[2], "Óscar")
        self.assertEqual(row[3], "Yetro")
        self.assertEqual(row[5], "")
        self.assertEqual(context.bot.sent_messages[0]["text"], "¡Pago registrado exitosamente! ✅")

