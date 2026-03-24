from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from domain.models import Movement
from domain.rules import DOUBLE_WEIGHT_PEOPLE, FIXED_GROUP_MEMBERS


def parse_amount(raw_value) -> float:
    return float(str(raw_value).replace("$", "").replace(",", ""))


def get_person_units(person_name: str) -> int:
    return 2 if person_name in DOUBLE_WEIGHT_PEOPLE else 1


def build_fixed_group(pagador: str) -> list[str]:
    return [name for name in FIXED_GROUP_MEMBERS if name != pagador]


def calculate_total_units(deudores: list[str]) -> int:
    return sum(get_person_units(deudor) for deudor in deudores) or 1


def calculate_share_amount(monto: float, deudores: list[str]) -> float:
    total_units = calculate_total_units(deudores)
    return round(monto / total_units, 2)


def calculate_debtor_amounts(monto: float, deudores: list[str]) -> list[tuple[str, float]]:
    monto_por_unidad = calculate_share_amount(monto, deudores)
    return [
        (deudor, monto_por_unidad * get_person_units(deudor))
        for deudor in deudores
    ]


def build_expense_summary(
    descripcion: str,
    monto: float,
    pagador: str,
    deudores: list[str],
    metodo: str | None = None,
) -> str:
    resumen = f"📌 *{descripcion}*\n💰 Monto total: ${monto:,.2f}\n👤 Pagó: {pagador}\n"
    if metodo:
        resumen += f"🏦 Método: {metodo}\n"

    resumen += "💸 Deudores:\n"
    for deudor, deuda in calculate_debtor_amounts(monto, deudores):
        resumen += f"• {deudor} paga ${deuda:,.2f}\n"

    return resumen


def build_expense_rows(
    descripcion: str,
    monto: float,
    pagador: str,
    deudores: list[str],
    timestamp: str,
    metodo: str = "",
) -> list[Movement]:
    movements = []
    for deudor, deuda in calculate_debtor_amounts(monto, deudores):
        movements.append(
            Movement(
                descripcion=descripcion,
                monto=deuda,
                deudor=deudor,
                acreedor=pagador,
                timestamp=timestamp,
                metodo_pago=metodo,
            )
        )
    return movements


def build_payment_summary(pagador: str, receptor: str, monto: float) -> str:
    return (
        "📌 *Confirmar pago*\n\n"
        f"👤 Pagador: {pagador}\n"
        f"➡️ Receptor: {receptor}\n"
        f"💵 Monto: ${monto:,.2f}\n\n"
        "¿Registrar este pago?"
    )


def build_payment_row(pagador: str, receptor: str, monto: float, timestamp: str) -> Movement:
    return Movement("Pago", -monto, pagador, receptor, timestamp, "")


def build_balance_map(movements: list[Movement]) -> dict[str, dict[str, float]]:
    balance: dict[str, dict[str, float]] = {}

    for movement in movements:
        deudor = movement.deudor
        acreedor = movement.acreedor
        monto = movement.monto

        balance.setdefault(deudor, {})
        balance.setdefault(acreedor, {})
        balance[deudor][acreedor] = balance[deudor].get(acreedor, 0) + monto

    return balance


def _format_currency(amount: float) -> str:
    rounded = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    normalized = rounded.normalize()
    text = format(normalized, "f")
    if "." not in text:
        text += ".0"
    return f"${text}"


def build_balance_summary(movements: list[Movement]) -> str:
    balance = build_balance_map(movements)
    resumen = "💳 *Saldos pendientes:*\n"

    for deudor, acreedores in balance.items():
        for acreedor, monto in acreedores.items():
            contraparte = balance.get(acreedor, {}).get(deudor, 0)
            neto = monto - contraparte
            if neto > 0:
                resumen += f"• {deudor} → {acreedor}: {_format_currency(round(neto, 2))}\n"

    if resumen.strip() == "💳 *Saldos pendientes:*":
        return "🎉 ¡Todo está saldado!"

    return resumen
