from __future__ import annotations

from dataclasses import dataclass

from domain.rules import PAYMENT_METHOD_OWNER


@dataclass(frozen=True)
class Movement:
    descripcion: str
    monto: float
    deudor: str
    acreedor: str
    timestamp: str
    metodo_pago: str = ""

    @classmethod
    def from_sheet_record(cls, record: dict) -> "Movement":
        return cls(
            descripcion=str(record.get("Descripcion", record.get("Descripción", ""))),
            monto=float(str(record["Monto"]).replace("$", "").replace(",", "")),
            deudor=record["Deudor"],
            acreedor=record["Prestador"],
            timestamp=str(record.get("Fecha", "")),
            metodo_pago=str(record.get("Metodo", record.get("Método", ""))),
        )

    def to_sheet_row(self) -> list:
        row = [self.descripcion, self.monto, self.deudor, self.acreedor, self.timestamp]
        if self.acreedor == PAYMENT_METHOD_OWNER:
            row.append(self.metodo_pago)
        return row
