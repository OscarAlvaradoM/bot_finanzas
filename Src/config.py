import os
from dotenv import load_dotenv

APP_ENV = os.getenv("APP_ENV", "dev")
ENV_FILE = f".env.{APP_ENV}"

load_dotenv(ENV_FILE)

TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
GOOGLE_WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "Hoja1")
MOVEMENTS_CACHE_TTL_SECONDS = float(os.getenv("MOVEMENTS_CACHE_TTL_SECONDS", "15"))

# Estados
DESCRIPCION, MONTO, PAGADOR, DEUDORES, NOMBRE_DEUDOR_EXTRA, INCLUIR_PAGADOR, METODO_PAGO, CONFIRMACION = range(8)
NOMBRE_PAGADOR_MANUAL = 99
(
    PAGAR_PAGADOR,
    PAGAR_PAGADOR_OTRO,
    PAGAR_RECEPTOR,
    PAGAR_RECEPTOR_OTRO,
    PAGAR_DECISION_MONTO,
    PAGAR_MONTO,
    PAGAR_CONFIRMAR,
) = range(100,107)

# Constantes
OPCIONES_PAGADORES = ["Óscar", "Yetro", "Judith", "Bichos", "Fabos"]
OPCIONES_DEUDORES = ["Óscar", "Yetro", "Judith", "Bichos", "Fabos"]
METODOS = ["Tarjeta", "Efectivo"]
