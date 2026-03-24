from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from domain.rules import PAYMENT_METHOD_OWNER


@dataclass(frozen=True)
class Movement:
    descripcion: str
    monto: float
    deudor: str
    acreedor: str
    timestamp: str
    metodo_pago: str = ""
    movement_id: str = ""

    @classmethod
    def from_sheet_record(cls, record: dict) -> "Movement":
        return cls(
            descripcion=str(record.get("Descripcion", record.get("Descripción", ""))),
            monto=float(str(record["Monto"]).replace("$", "").replace(",", "")),
            deudor=record["Deudor"],
            acreedor=record["Prestador"],
            timestamp=str(record.get("Fecha", "")),
            metodo_pago=str(record.get("Metodo", record.get("Método", ""))),
            movement_id=str(record.get("MovementId", "")),
        )

    def to_sheet_row(self) -> list:
        return [
            self.descripcion,
            _serialize_amount(self.monto),
            self.deudor,
            self.acreedor,
            self.timestamp,
            self.metodo_pago if self.acreedor == PAYMENT_METHOD_OWNER else "",
            self.movement_id,
        ]


def _serialize_amount(value: float) -> str:
    normalized = Decimal(str(value)).normalize()
    return format(normalized, "f")
