import asyncio
import unittest
from unittest.mock import patch

from tests.helpers import FakeContext, FakeMessage, FakeSheet, FakeUpdate

from handlers.saldo import saldo


class SaldoTests(unittest.TestCase):
    def test_saldo_netea_deudas_cruzadas(self):
        sheet = FakeSheet(
            records=[
                {"Deudor": "Óscar", "Prestador": "Yetro", "Monto": "500"},
                {"Deudor": "Yetro", "Prestador": "Óscar", "Monto": "200"},
            ]
        )
        message = FakeMessage()
        update = FakeUpdate(message=message)

        with patch("handlers.saldo.init_gsheet", return_value=sheet):
            asyncio.run(saldo(update, FakeContext()))

        self.assertEqual(message.replies[0]["text"], "Calculando saldos...")
        self.assertIn("Óscar → Yetro: $300.0", message.replies[1]["text"])
        self.assertNotIn("Yetro → Óscar", message.replies[1]["text"])

    def test_saldo_reduce_deuda_con_pago_negativo(self):
        sheet = FakeSheet(
            records=[
                {"Deudor": "Óscar", "Prestador": "Yetro", "Monto": "500"},
                {"Deudor": "Óscar", "Prestador": "Yetro", "Monto": "-150"},
            ]
        )
        message = FakeMessage()
        update = FakeUpdate(message=message)

        with patch("handlers.saldo.init_gsheet", return_value=sheet):
            asyncio.run(saldo(update, FakeContext()))

        self.assertIn("Óscar → Yetro: $350.0", message.replies[1]["text"])

