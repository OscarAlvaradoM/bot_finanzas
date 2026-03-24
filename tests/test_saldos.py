import asyncio
import unittest
from unittest.mock import patch

from domain.errors import RepositoryError
from domain.models import Movement
from tests.helpers import FakeContext, FakeMessage, FakeUpdate

from handlers.saldo import saldo
from services.finance_service import (
    build_balance_summary,
    build_people_totals_summary,
    get_total_credit_by_person,
    get_total_debt_by_person,
)


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

        self.assertEqual(message.replies[0]["text"], "📊 Calculando saldos...")
        self.assertIn("Óscar: $300.0", message.replies[1]["text"])
        self.assertIn("*Óscar*", message.replies[2]["text"])
        self.assertIn("Debe a Yetro: $300.0", message.replies[2]["text"])
        self.assertNotIn("Yetro → Óscar", message.replies[2]["text"])

    def test_saldo_reduce_deuda_con_pago_negativo(self):
        movements = [
            Movement("Cena", 500.0, "Óscar", "Yetro", "2026-03-23 10:00:00"),
            Movement("Pago", -150.0, "Óscar", "Yetro", "2026-03-23 12:00:00"),
        ]
        message = FakeMessage()
        update = FakeUpdate(message=message)

        with patch("handlers.saldo.fetch_movements", return_value=movements):
            asyncio.run(saldo(update, FakeContext()))

        self.assertEqual(message.replies[0]["text"], "📊 Calculando saldos...")
        self.assertIn("Óscar: $350.0", message.replies[1]["text"])
        self.assertIn("Debe a Yetro: $350.0", message.replies[2]["text"])

    def test_build_balance_summary_muestra_todo_saldado_si_no_hay_deuda(self):
        summary = build_balance_summary(
            [
                Movement("Cena", 100.0, "Óscar", "Yetro", "2026-03-23 10:00:00"),
                Movement("Pago", 100.0, "Yetro", "Óscar", "2026-03-23 11:00:00"),
            ]
        )

        self.assertEqual(summary, "🎉 ¡Todo está saldado!")

    def test_totales_por_persona(self):
        movements = [
            Movement("Cena", 500.0, "Óscar", "Yetro", "2026-03-23 10:00:00"),
            Movement("Comida", 200.0, "Óscar", "Judith", "2026-03-23 11:00:00"),
            Movement("Pago", -150.0, "Óscar", "Yetro", "2026-03-23 12:00:00"),
        ]

        self.assertEqual(get_total_debt_by_person(movements), {"Óscar": 550.0})
        self.assertEqual(get_total_credit_by_person(movements), {"Judith": 200.0, "Yetro": 350.0})

    def test_build_people_totals_summary_muestra_totales(self):
        summary = build_people_totals_summary(
            [
                Movement("Cena", 500.0, "Óscar", "Yetro", "2026-03-23 10:00:00"),
                Movement("Comida", 200.0, "Óscar", "Judith", "2026-03-23 11:00:00"),
                Movement("Pago", -150.0, "Óscar", "Yetro", "2026-03-23 12:00:00"),
            ]
        )

        self.assertIn("Total que debe cada persona", summary)
        self.assertIn("Óscar: $550.0", summary)
        self.assertIn("Judith: $200.0", summary)
        self.assertIn("Yetro: $350.0", summary)

    def test_saldo_muestra_error_si_falla_consulta(self):
        message = FakeMessage()
        update = FakeUpdate(message=message)

        with patch("handlers.saldo.fetch_movements", side_effect=RepositoryError("fallo")):
            asyncio.run(saldo(update, FakeContext()))

        self.assertEqual(message.replies[0]["text"], "📊 Calculando saldos...")
        self.assertEqual(
            message.replies[1]["text"],
            "❌ No pude consultar los saldos en este momento.\n\nIntenta de nuevo más tarde.",
        )

    def test_saldo_muestra_resumen_por_persona_y_detalle(self):
        movements = [
            Movement("Cena", 500.0, "Óscar", "Yetro", "2026-03-23 10:00:00"),
            Movement("Comida", 200.0, "Óscar", "Judith", "2026-03-23 11:00:00"),
            Movement("Pago", -150.0, "Óscar", "Yetro", "2026-03-23 12:00:00"),
        ]
        message = FakeMessage()
        update = FakeUpdate(message=message)

        with patch("handlers.saldo.fetch_movements", return_value=movements):
            asyncio.run(saldo(update, FakeContext()))

        self.assertEqual(message.replies[0]["text"], "📊 Calculando saldos...")
        self.assertIn("Resumen por persona", message.replies[1]["text"])
        self.assertIn("Saldos pendientes por deudor", message.replies[2]["text"])
