import asyncio
import unittest
from unittest.mock import patch

from tests.helpers import FakeCallbackQuery, FakeContext, FakeUpdate

from handlers.pago import pagar_confirmar
from services.finance_service import build_payment_row
from telegram.ext import ConversationHandler


class PagoTests(unittest.TestCase):
    def test_pagar_confirmar_registra_monto_negativo(self):
        update = FakeUpdate(callback_query=FakeCallbackQuery("confirmar_pago"))
        context = FakeContext(
            user_data={
                "pagador": "Óscar",
                "receptor": "Yetro",
                "monto": 250.0,
            }
        )

        with patch("handlers.pago.append_row") as mocked_append_row:
            state = asyncio.run(pagar_confirmar(update, context))

        self.assertEqual(state, ConversationHandler.END)
        row = mocked_append_row.call_args.args[0]
        self.assertEqual(row[0], "Pago")
        self.assertEqual(row[1], -250.0)
        self.assertEqual(row[2], "Óscar")
        self.assertEqual(row[3], "Yetro")
        self.assertEqual(row[5], "")
        self.assertEqual(context.bot.sent_messages[0]["text"], "¡Pago registrado exitosamente! ✅")

    def test_build_payment_row_crea_formato_esperado(self):
        row = build_payment_row("Óscar", "Yetro", 250.0, "2026-03-23 11:00:00")

        self.assertEqual(row, ["Pago", -250.0, "Óscar", "Yetro", "2026-03-23 11:00:00", ""])
