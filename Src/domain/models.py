from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from domain.rules import PAYMENT_METHOD_OWNER
from domain.schema import SHEET_COLUMNS


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
            descripcion=str(_get_record_value(record, "descripcion", "")),
            monto=float(str(_get_record_value(record, "monto", "0")).replace("$", "").replace(",", "")),
            deudor=str(_get_record_value(record, "deudor", "")),
            acreedor=str(_get_record_value(record, "acreedor", "")),
            timestamp=str(_get_record_value(record, "timestamp", "")),
            metodo_pago=str(_get_record_value(record, "metodo_pago", "")),
            movement_id=str(_get_record_value(record, "movement_id", "")),
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


def _get_record_value(record: dict, field_name: str, default):
    for column_name in SHEET_COLUMNS[field_name]:
        if column_name in record:
            return record[column_name]
    return default


@dataclass
class ExpenseDraft:
    descripcion: str = ""
    monto: float = 0.0
    pagador: str = ""
    deudores: list[str] = field(default_factory=list)
    metodo_pago: str = ""
    movement_id: str = ""
    processed: bool = False
    mensaje_descripcion_id: int | None = None
    mensaje_monto_id: int | None = None
    primer_pregunta_deudores: bool = True

    def add_deudor(self, deudor: str) -> bool:
        if deudor in self.deudores or deudor == self.pagador:
            return False
        self.deudores.append(deudor)
        self.primer_pregunta_deudores = False
        return True

    def add_deudores(self, nuevos_deudores: list[str]) -> None:
        for deudor in nuevos_deudores:
            if deudor not in self.deudores and deudor != self.pagador:
                self.deudores.append(deudor)
        if nuevos_deudores:
            self.primer_pregunta_deudores = False

    def include_pagador(self) -> None:
        if self.pagador and self.pagador not in self.deudores:
            self.deudores.append(self.pagador)


@dataclass
class PaymentDraft:
    pagador: str = ""
    receptor: str = ""
    monto: float = 0.0
    movement_id: str = ""
    processed: bool = False
