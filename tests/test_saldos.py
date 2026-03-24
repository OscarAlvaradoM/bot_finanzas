import asyncio
import unittest
from unittest.mock import patch

from domain.models import Movement
from tests.helpers import FakeContext, FakeMessage, FakeUpdate

from handlers.saldo import saldo
from services.finance_service import build_balance_summary


class SaldoTests(unittest.TestCase):
    def test_saldo_netea_deudas_cruzadas(self):
        movements = [
            Movement("Cena", 500.0, "Óscar", "Yetro", "2026-03-23 10:00:00"),
            Movement("Comida", 200.0, "Yetro", "Óscar", "2026-03-23 11:00:00"),
        ]
        message = FakeMessage()
        update = FakeUpdate(message=message)

        with patch("handlers.saldo.fetch_movements", return_value=movements):
            asyncio.run(saldo(update, FakeContext()))

        self.assertEqual(message.replies[0]["text"], "Calculando saldos...")
        self.assertIn("Óscar → Yetro: $300.0", message.replies[1]["text"])
        self.assertNotIn("Yetro → Óscar", message.replies[1]["text"])

    def test_saldo_reduce_deuda_con_pago_negativo(self):
        movements = [
            Movement("Cena", 500.0, "Óscar", "Yetro", "2026-03-23 10:00:00"),
            Movement("Pago", -150.0, "Óscar", "Yetro", "2026-03-23 12:00:00"),
        ]
        message = FakeMessage()
        update = FakeUpdate(message=message)

        with patch("handlers.saldo.fetch_movements", return_value=movements):
            asyncio.run(saldo(update, FakeContext()))

        self.assertIn("Óscar → Yetro: $350.0", message.replies[1]["text"])

    def test_build_balance_summary_muestra_todo_saldado_si_no_hay_deuda(self):
        summary = build_balance_summary(
            [
                Movement("Cena", 100.0, "Óscar", "Yetro", "2026-03-23 10:00:00"),
                Movement("Pago", 100.0, "Yetro", "Óscar", "2026-03-23 11:00:00"),
            ]
        )

        self.assertEqual(summary, "🎉 ¡Todo está saldado!")
