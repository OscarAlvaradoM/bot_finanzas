import unittest
from unittest.mock import patch

from domain.models import Movement
from repositories.sheets_repository import append_movements, fetch_movements
from tests.helpers import FakeSheet


class SheetsRepositoryTests(unittest.TestCase):
    def test_fetch_movements_asegura_columna_movement_id(self):
        sheet = FakeSheet(
            records=[
                {
                    "Descripcion": "Cena",
                    "Monto": "100",
                    "Deudor": "Óscar",
                    "Prestador": "Yetro",
                    "Fecha": "2026-03-23 10:00:00",
                    "Metodo": "",
                }
            ]
        )

        with patch("repositories.sheets_repository.init_gsheet", return_value=sheet):
            movements = fetch_movements()

        self.assertEqual(sheet.headers[-1], "MovementId")
        self.assertEqual(movements[0].movement_id, "")

    def test_append_movements_omite_movement_id_duplicado(self):
        movement = Movement(
            "Cena",
            100.0,
            "Óscar",
            "Yetro",
            "2026-03-23 10:00:00",
            "",
            "dup-123",
        )
        sheet = FakeSheet(
            records=[
                {
                    "Descripcion": "Cena",
                    "Monto": "100",
                    "Deudor": "Óscar",
                    "Prestador": "Yetro",
                    "Fecha": "2026-03-23 10:00:00",
                    "Metodo": "",
                    "MovementId": "dup-123",
                }
            ],
            headers=["Descripcion", "Monto", "Deudor", "Prestador", "Fecha", "Metodo", "MovementId"],
        )

        with patch("repositories.sheets_repository.init_gsheet", return_value=sheet):
            append_movements([movement])

        self.assertEqual(sheet.rows, [])
