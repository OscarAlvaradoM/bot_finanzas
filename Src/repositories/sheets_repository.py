import logging
import time
from typing import Optional

from config import MOVEMENTS_CACHE_TTL_SECONDS
from domain.errors import RepositoryError
from domain.models import Movement
from domain.schema import SHEET_HEADERS
from sheets import init_gsheet

logger = logging.getLogger(__name__)
_movements_cache: dict[str, object] = {
    "items": None,
    "expires_at": 0.0,
}


def _ensure_sheet_schema(sheet) -> None:
    headers = sheet.row_values(1)
    if headers == SHEET_HEADERS:
        return

    for index, header in enumerate(SHEET_HEADERS, start=1):
        if len(headers) < index or headers[index - 1] != header:
            sheet.update_cell(1, index, header)


def _get_cached_movements() -> Optional[list[Movement]]:
    cached_items = _movements_cache["items"]
    expires_at = _movements_cache["expires_at"]

    if cached_items is None or time.monotonic() >= expires_at:
        return None

    return list(cached_items)


def _store_movements_cache(movements: list[Movement]) -> None:
    _movements_cache["items"] = list(movements)
    _movements_cache["expires_at"] = time.monotonic() + MOVEMENTS_CACHE_TTL_SECONDS


def invalidate_movements_cache() -> None:
    _movements_cache["items"] = None
    _movements_cache["expires_at"] = 0.0


def fetch_movements() -> list[Movement]:
    try:
        cached_movements = _get_cached_movements()
        if cached_movements is not None:
            return cached_movements

        sheet = init_gsheet()
        _ensure_sheet_schema(sheet)
        movements = [Movement.from_sheet_record(record) for record in sheet.get_all_records()]
        _store_movements_cache(movements)
        return movements
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
        wrote_any = False

        for movement in movements:
            if movement.movement_id and movement.movement_id in existing_ids:
                continue
            sheet.append_row(movement.to_sheet_row())
            wrote_any = True

        if wrote_any:
            invalidate_movements_cache()
    except RepositoryError:
        raise
    except Exception as exc:
        logger.exception("Error al guardar movimientos en Google Sheets")
        raise RepositoryError("No se pudieron guardar los movimientos.") from exc


def append_movement(movement: Movement) -> None:
    append_movements([movement])
