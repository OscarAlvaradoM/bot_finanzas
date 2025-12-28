import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH")

# Estados
DESCRIPCION, MONTO, PAGADOR, DEUDORES, NOMBRE_DEUDOR_EXTRA, INCLUIR_PAGADOR, METODO_PAGO, CONFIRMACION = range(8)
NOMBRE_PAGADOR_MANUAL = 99
(
    PAGAR_PAGADOR,
    PAGAR_PAGADOR_OTRO,
    PAGAR_RECEPTOR,
    PAGAR_RECEPTOR_OTRO,
    PAGAR_MONTO,
    PAGAR_CONFIRMAR,
) = range(100,106)

# Constantes
OPCIONES_PAGADORES = ["Óscar", "Yetro", "Judith", "Bichos", "Fabos"]
OPCIONES_DEUDORES = ["Óscar", "Yetro", "Judith", "Bichos", "Fabos"]
METODOS = ["Tarjeta", "Efectivo"]