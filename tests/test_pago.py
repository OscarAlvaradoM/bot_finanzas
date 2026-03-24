import asyncio
import unittest
from unittest.mock import patch

from domain.errors import RepositoryError
from domain.models import Movement, PaymentDraft
from tests.helpers import FakeCallbackQuery, FakeContext, FakeUpdate

from config import PAGAR_CONFIRMAR, PAGAR_DECISION_MONTO, PAGAR_MONTO, PAGAR_PAGADOR, PAGAR_RECEPTOR
from handlers.pago import pagar, pagar_confirmar, pagar_decidir_monto, pagar_pagador, pagar_receptor
from services.finance_service import build_payment_row, get_creditors_for_debtor, get_debt_amount, get_people_with_debt
from telegram.ext import ConversationHandler


class PagoTests(unittest.TestCase):
    def test_get_people_with_debt_y_receptores_desde_saldos(self):
        movements = [
            Movement("Cena", 500.0, "Óscar", "Yetro", "2026-03-23 10:00:00"),
            Movement("Comida", 200.0, "Óscar", "Judith", "2026-03-23 11:00:00"),
            Movement("Pago", -150.0, "Óscar", "Yetro", "2026-03-23 12:00:00"),
        ]

        self.assertEqual(get_people_with_debt(movements), ["Óscar"])
        self.assertEqual(get_creditors_for_debtor(movements, "Óscar"), ["Judith", "Yetro"])
        self.assertEqual(get_debt_amount(movements, "Óscar", "Yetro"), 350.0)

    def test_pagar_muestra_pagadores_con_deuda_y_otro(self):
        bot_movements = [Movement("Cena", 500.0, "Óscar", "Yetro", "2026-03-23 10:00:00")]
        update = FakeUpdate(message=type("Msg", (), {"reply_text": None})())
        context = FakeContext()

        async def fake_reply_text(text, **kwargs):
            context.bot.sent_messages.append({"text": text, **kwargs})

        update.message.reply_text = fake_reply_text

        with patch("handlers.pago.fetch_movements", return_value=bot_movements):
            state = asyncio.run(pagar(update, context))

        self.assertEqual(state, PAGAR_PAGADOR)
        keyboard = context.bot.sent_messages[0]["reply_markup"].keyboard
        labels = [row[0].text for row in keyboard]
        self.assertEqual(labels, ["Óscar", "Otro"])

    def test_pagar_pagador_muestra_receptores_con_deuda(self):
        movements = [
            Movement("Cena", 500.0, "Óscar", "Yetro", "2026-03-23 10:00:00"),
            Movement("Comida", 200.0, "Óscar", "Judith", "2026-03-23 11:00:00"),
        ]
        update = FakeUpdate(callback_query=FakeCallbackQuery("Óscar"))
        context = FakeContext(user_data={"payment_draft": PaymentDraft()})

        with patch("handlers.pago.fetch_movements", return_value=movements):
            state = asyncio.run(pagar_pagador(update, context))

        self.assertEqual(state, PAGAR_RECEPTOR)
        keyboard = update.callback_query.edits[0]["reply_markup"].keyboard
        labels = [row[0].text for row in keyboard]
        self.assertEqual(labels, ["Judith", "Yetro", "Otro"])

    def test_pagar_receptor_ofrece_liquidar_deuda_u_otro_monto(self):
        movements = [Movement("Cena", 500.0, "Óscar", "Yetro", "2026-03-23 10:00:00")]
        update = FakeUpdate(callback_query=FakeCallbackQuery("Yetro"))
        context = FakeContext(
            user_data={"payment_draft": PaymentDraft(pagador="Óscar")}
        )

        with patch("handlers.pago.fetch_movements", return_value=movements):
            state = asyncio.run(pagar_receptor(update, context))

        self.assertEqual(state, PAGAR_DECISION_MONTO)
        self.assertEqual(context.user_data["payment_draft"].deuda_sugerida, 500.0)
        self.assertIn("un total de $500.00", update.callback_query.edits[0]["text"])

    def test_pagar_decidir_monto_liquida_deuda_y_pasa_a_confirmacion(self):
        update = FakeUpdate(callback_query=FakeCallbackQuery("liquidar_deuda"))
        draft = PaymentDraft(pagador="Óscar", receptor="Yetro", deuda_sugerida=350.0)
        context = FakeContext(user_data={"payment_draft": draft})

        state = asyncio.run(pagar_decidir_monto(update, context))

        self.assertEqual(state, PAGAR_CONFIRMAR)
        self.assertEqual(draft.monto, 350.0)
        self.assertIn("Monto: $350.00", update.callback_query.edits[0]["text"])

    def test_pagar_decidir_monto_pide_otro_monto(self):
        update = FakeUpdate(callback_query=FakeCallbackQuery("otro_monto"))
        draft = PaymentDraft(pagador="Óscar", receptor="Yetro", deuda_sugerida=350.0)
        context = FakeContext(user_data={"payment_draft": draft})

        state = asyncio.run(pagar_decidir_monto(update, context))

        self.assertEqual(state, PAGAR_MONTO)
        self.assertIn("¿Cuánto pagó", update.callback_query.edits[0]["text"])

    def test_pagar_confirmar_registra_monto_negativo(self):
        update = FakeUpdate(callback_query=FakeCallbackQuery("confirmar_pago"))
        context = FakeContext(
            user_data={
                "payment_draft": PaymentDraft(
                    pagador="Óscar",
                    receptor="Yetro",
                    monto=250.0,
                    movement_id="pago-123",
                ),
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
        self.assertEqual(movement.movement_id, "pago-123")
        self.assertEqual(context.bot.sent_messages[0]["text"], "¡Pago registrado exitosamente! ✅")
        self.assertEqual(
            update.callback_query.edits[0]["text"],
            "✅ Pago registrado. Esta confirmación ya quedó cerrada.",
        )

    def test_pagar_confirmar_no_registra_dos_veces(self):
        update = FakeUpdate(callback_query=FakeCallbackQuery("confirmar_pago"))
        context = FakeContext(
            user_data={
                "payment_draft": PaymentDraft(
                    pagador="Óscar",
                    receptor="Yetro",
                    monto=250.0,
                    movement_id="pago-123",
                ),
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

    def test_pagar_confirmar_muestra_error_si_falla_persistencia(self):
        update = FakeUpdate(callback_query=FakeCallbackQuery("confirmar_pago"))
        draft = PaymentDraft(
            pagador="Óscar",
            receptor="Yetro",
            monto=250.0,
            movement_id="pago-123",
        )
        context = FakeContext(user_data={"payment_draft": draft})

        with patch("handlers.pago.append_movement", side_effect=RepositoryError("fallo")):
            state = asyncio.run(pagar_confirmar(update, context))

        self.assertEqual(state, PAGAR_CONFIRMAR)
        self.assertFalse(draft.processed)
        self.assertEqual(
            update.callback_query.edits[-1]["text"],
            "❌ No pude registrar el pago. Intenta de nuevo en unos minutos.",
        )

    def test_build_payment_row_crea_formato_esperado(self):
        movement = build_payment_row("Óscar", "Yetro", 250.0, "2026-03-23 11:00:00")

        self.assertEqual(
            movement,
            Movement("Pago", -250.0, "Óscar", "Yetro", "2026-03-23 11:00:00", "", ""),
        )
