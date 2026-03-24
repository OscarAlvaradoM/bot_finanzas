import asyncio
import unittest
from unittest.mock import patch

from domain.models import Movement
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

        with patch("handlers.pago.append_movement") as mocked_append_movement:
            state = asyncio.run(pagar_confirmar(update, context))

        self.assertEqual(state, ConversationHandler.END)
        movement = mocked_append_movement.call_args.args[0]
        self.assertEqual(movement.descripcion, "Pago")
        self.assertEqual(movement.monto, -250.0)
        self.assertEqual(movement.deudor, "Óscar")
        self.assertEqual(movement.acreedor, "Yetro")
        self.assertEqual(movement.metodo_pago, "")
        self.assertTrue(movement.movement_id)
        self.assertEqual(context.bot.sent_messages[0]["text"], "¡Pago registrado exitosamente! ✅")
        self.assertEqual(
            update.callback_query.edits[0]["text"],
            "✅ Pago registrado. Esta confirmación ya quedó cerrada.",
        )

    def test_pagar_confirmar_no_registra_dos_veces(self):
        update = FakeUpdate(callback_query=FakeCallbackQuery("confirmar_pago"))
        context = FakeContext(
            user_data={
                "pagador": "Óscar",
                "receptor": "Yetro",
                "monto": 250.0,
            }
        )

        with patch("handlers.pago.append_movement") as mocked_append_movement:
            first_state = asyncio.run(pagar_confirmar(update, context))
            second_state = asyncio.run(pagar_confirmar(update, context))

        self.assertEqual(first_state, ConversationHandler.END)
        self.assertEqual(second_state, ConversationHandler.END)
        self.assertEqual(mocked_append_movement.call_count, 1)
        self.assertEqual(
            update.callback_query.edits[-1]["text"],
            "⚠️ Este pago ya fue registrado anteriormente.",
        )

    def test_build_payment_row_crea_formato_esperado(self):
        movement = build_payment_row("Óscar", "Yetro", 250.0, "2026-03-23 11:00:00")

        self.assertEqual(
            movement,
            Movement("Pago", -250.0, "Óscar", "Yetro", "2026-03-23 11:00:00", "", ""),
        )
