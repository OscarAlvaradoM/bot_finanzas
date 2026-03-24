import os
import pathlib
import sys
import unittest

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "Src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@unittest.skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS") == "1",
    "Define RUN_INTEGRATION_TESTS=1 para ejecutar integracion con Google Sheets.",
)
class SheetsSmokeTests(unittest.TestCase):
    def test_abre_worksheet_configurada(self):
        try:
            import dotenv  # noqa: F401
            import gspread  # noqa: F401
            from oauth2client.service_account import ServiceAccountCredentials  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"Faltan dependencias reales para integracion: {exc}")

        from config import GOOGLE_WORKSHEET_NAME
        from sheets import init_gsheet

        if not os.getenv("GOOGLE_CREDS_PATH") or not os.getenv("GOOGLE_SHEET_NAME"):
            self.skipTest(
                "Faltan variables de entorno. Ejecuta con APP_ENV=dev y un entorno que cargue .env.dev."
            )

        worksheet = init_gsheet()

        self.assertIsNotNone(worksheet)
        self.assertEqual(worksheet.title, GOOGLE_WORKSHEET_NAME)
        self.assertIsInstance(worksheet.get_all_values(), list)
