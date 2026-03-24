from sheets import init_gsheet


def fetch_records() -> list[dict]:
    sheet = init_gsheet()
    return sheet.get_all_records()


def append_rows(rows: list[list]) -> None:
    sheet = init_gsheet()
    for row in rows:
        sheet.append_row(row)


def append_row(row: list) -> None:
    append_rows([row])
