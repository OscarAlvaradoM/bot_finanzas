from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import uuid
from domain.models import Movement
from domain.rules import DOUBLE_WEIGHT_PEOPLE, FIXED_GROUP_MEMBERS


def parse_amount(raw_value) -> float:
    return float(str(raw_value).replace("$", "").replace(",", ""))


def generate_movement_id() -> str:
    return uuid.uuid4().hex


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
    movement_id: str = "",
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
                movement_id=movement_id,
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


def build_payment_row(
    pagador: str,
    receptor: str,
    monto: float,
    timestamp: str,
    movement_id: str = "",
) -> Movement:
    return Movement("Pago", -monto, pagador, receptor, timestamp, "", movement_id)


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
    net_balances = get_net_balances(movements)
    resumen = "💳 *Saldos pendientes por deudor:*\n"

    for deudor, acreedores in sorted(net_balances.items()):
        resumen += f"\n*{deudor}*\n"
        for acreedor, monto in sorted(acreedores.items()):
            resumen += f"• Debe a {acreedor}: {_format_currency(round(monto, 2))}\n"

    if resumen.strip() == "💳 *Saldos pendientes por deudor:*":
        return "🎉 ¡Todo está saldado!"

    return resumen


def get_net_balances(movements: list[Movement]) -> dict[str, dict[str, float]]:
    balance = build_balance_map(movements)
    net_balances: dict[str, dict[str, float]] = {}

    for deudor, acreedores in balance.items():
        for acreedor, monto in acreedores.items():
            contraparte = balance.get(acreedor, {}).get(deudor, 0)
            neto = round(monto - contraparte, 2)
            if neto > 0:
                net_balances.setdefault(deudor, {})[acreedor] = neto

    return net_balances


def get_people_with_debt(movements: list[Movement]) -> list[str]:
    return sorted(get_net_balances(movements).keys())


def get_creditors_for_debtor(movements: list[Movement], deudor: str) -> list[str]:
    return sorted(get_net_balances(movements).get(deudor, {}).keys())


def get_debt_amount(movements: list[Movement], deudor: str, acreedor: str) -> float:
    return get_net_balances(movements).get(deudor, {}).get(acreedor, 0.0)


def get_total_debt_by_person(movements: list[Movement]) -> dict[str, float]:
    net_balances = get_net_balances(movements)
    return {
        person: round(sum(acreedores.values()), 2)
        for person, acreedores in net_balances.items()
    }


def get_total_credit_by_person(movements: list[Movement]) -> dict[str, float]:
    net_balances = get_net_balances(movements)
    credits: dict[str, float] = {}

    for acreedores in net_balances.values():
        for acreedor, monto in acreedores.items():
            credits[acreedor] = round(credits.get(acreedor, 0) + monto, 2)

    return credits


def build_people_totals_summary(movements: list[Movement]) -> str:
    total_debt = get_total_debt_by_person(movements)
    total_credit = get_total_credit_by_person(movements)

    if not total_debt and not total_credit:
        return "🎉 ¡Todo está saldado!"

    resumen = "👥 *Resumen por persona:*\n"

    if total_debt:
        resumen += "\n*Total que debe cada persona:*\n"
        for person, amount in sorted(total_debt.items()):
            resumen += f"• {person}: {_format_currency(amount)}\n"

    if total_credit:
        resumen += "\n*Total que le deben a cada persona:*\n"
        for person, amount in sorted(total_credit.items()):
            resumen += f"• {person}: {_format_currency(amount)}\n"

    return resumen
