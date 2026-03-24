from domain.models import Movement
from sheets import init_gsheet


def fetch_movements() -> list[Movement]:
    sheet = init_gsheet()
    return [Movement.from_sheet_record(record) for record in sheet.get_all_records()]


def append_movements(movements: list[Movement]) -> None:
    sheet = init_gsheet()
    for movement in movements:
        sheet.append_row(movement.to_sheet_row())


def append_movement(movement: Movement) -> None:
    append_movements([movement])
