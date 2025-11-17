# config.py
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH")

# Estados
DESCRIPCION, MONTO, PAGADOR, DEUDORES, NOMBRE_DEUDOR_EXTRA, INCLUIR_PAGADOR, METODO_PAGO, CONFIRMACION = range(8)
NOMBRE_PAGADOR_MANUAL = 99

# Constantes
OPCIONES_PAGADORES = ["Óscar", "Yetro", "Bichos", "Fabos"]
OPCIONES_DEUDORES = ["Óscar", "Yetro", "Bichos", "Fabos"]
METODOS = ["Santander Oro", "Rappi", "BBVA", "LikeU", "Banamex", "Efectivo"]