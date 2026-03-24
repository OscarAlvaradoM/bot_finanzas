import unittest
from unittest.mock import patch

from domain.models import Movement
from repositories import sheets_repository
from repositories.sheets_repository import append_movements, fetch_movements, invalidate_movements_cache
from tests.helpers import FakeSheet


class SheetsRepositoryTests(unittest.TestCase):
    def tearDown(self):
        invalidate_movements_cache()

    def test_fetch_movements_acepta_alias_de_columnas_heredadas(self):
        sheet = FakeSheet(
            records=[
                {
                    "Descripción": "Cena",
                    "Monto": "100",
                    "Deudor": "Óscar",
                    "Acreedor": "Yetro",
                    "Fecha": "2026-03-23 10:00:00",
                    "Método": "Tarjeta",
                    "MovementId": "mov-1",
                }
            ],
            headers=["Descripción", "Monto", "Deudor", "Acreedor", "Fecha", "Método", "MovementId"],
        )

        with patch("repositories.sheets_repository.init_gsheet", return_value=sheet):
            movements = fetch_movements()

        self.assertEqual(movements[0].descripcion, "Cena")
        self.assertEqual(movements[0].acreedor, "Yetro")
        self.assertEqual(movements[0].metodo_pago, "Tarjeta")
        self.assertEqual(movements[0].movement_id, "mov-1")

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

    def test_fetch_movements_reutiliza_cache_durante_ttl(self):
        sheet = FakeSheet(
            records=[
                {
                    "Descripcion": "Cena",
                    "Monto": "100",
                    "Deudor": "Óscar",
                    "Prestador": "Yetro",
                    "Fecha": "2026-03-23 10:00:00",
                    "Metodo": "",
                    "MovementId": "mov-1",
                }
            ],
            headers=["Descripcion", "Monto", "Deudor", "Prestador", "Fecha", "Metodo", "MovementId"],
        )

        with patch("repositories.sheets_repository.init_gsheet", return_value=sheet) as mock_init:
            first = fetch_movements()
            second = fetch_movements()

        self.assertEqual(mock_init.call_count, 1)
        self.assertEqual(first[0].movement_id, second[0].movement_id)

    def test_fetch_movements_vuelve_a_leer_cuando_expira_cache(self):
        sheet = FakeSheet(
            records=[
                {
                    "Descripcion": "Cena",
                    "Monto": "100",
                    "Deudor": "Óscar",
                    "Prestador": "Yetro",
                    "Fecha": "2026-03-23 10:00:00",
                    "Metodo": "",
                    "MovementId": "mov-1",
                }
            ],
            headers=["Descripcion", "Monto", "Deudor", "Prestador", "Fecha", "Metodo", "MovementId"],
        )

        with patch("repositories.sheets_repository.init_gsheet", return_value=sheet) as mock_init:
            with patch.object(sheets_repository, "MOVEMENTS_CACHE_TTL_SECONDS", 0):
                fetch_movements()
                fetch_movements()

        self.assertEqual(mock_init.call_count, 2)

    def test_append_movements_invalida_cache_tras_guardar(self):
        existing_sheet = FakeSheet(
            records=[
                {
                    "Descripcion": "Cena",
                    "Monto": "100",
                    "Deudor": "Óscar",
                    "Prestador": "Yetro",
                    "Fecha": "2026-03-23 10:00:00",
                    "Metodo": "",
                    "MovementId": "mov-1",
                }
            ],
            headers=["Descripcion", "Monto", "Deudor", "Prestador", "Fecha", "Metodo", "MovementId"],
        )
        movement = Movement(
            "Taxi",
            50.0,
            "Óscar",
            "Judith",
            "2026-03-24 10:00:00",
            "",
            "mov-2",
        )

        with patch("repositories.sheets_repository.init_gsheet", return_value=existing_sheet) as mock_init:
            fetch_movements()
            append_movements([movement])
            fetch_movements()

        self.assertEqual(mock_init.call_count, 3)
