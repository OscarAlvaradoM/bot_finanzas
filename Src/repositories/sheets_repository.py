import logging

from domain.errors import RepositoryError
from domain.models import Movement
from domain.schema import SHEET_HEADERS
from sheets import init_gsheet

logger = logging.getLogger(__name__)


def _ensure_sheet_schema(sheet) -> None:
    headers = sheet.row_values(1)
    if headers == SHEET_HEADERS:
        return

    for index, header in enumerate(SHEET_HEADERS, start=1):
        if len(headers) < index or headers[index - 1] != header:
            sheet.update_cell(1, index, header)


def fetch_movements() -> list[Movement]:
    try:
        sheet = init_gsheet()
        _ensure_sheet_schema(sheet)
        return [Movement.from_sheet_record(record) for record in sheet.get_all_records()]
    except Exception as exc:
        logger.exception("Error al leer movimientos desde Google Sheets")
        raise RepositoryError("No se pudieron leer los movimientos.") from exc


def append_movements(movements: list[Movement]) -> None:
    if not movements:
        return

    try:
        sheet = init_gsheet()
        _ensure_sheet_schema(sheet)
        existing_ids = {
            movement.movement_id
            for movement in fetch_movements()
            if movement.movement_id
        }

        for movement in movements:
            if movement.movement_id and movement.movement_id in existing_ids:
                continue
            sheet.append_row(movement.to_sheet_row())
    except RepositoryError:
        raise
    except Exception as exc:
        logger.exception("Error al guardar movimientos en Google Sheets")
        raise RepositoryError("No se pudieron guardar los movimientos.") from exc


def append_movement(movement: Movement) -> None:
    append_movements([movement])
