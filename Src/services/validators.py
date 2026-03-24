from typing import Optional

from services.finance_service import parse_amount


def is_expected_reply(message, expected_message_id: Optional[int]) -> bool:
    if expected_message_id is None:
        return True
    if not getattr(message, "reply_to_message", None):
        return True
    return message.reply_to_message.message_id == expected_message_id


def validate_amount_text(raw_text: str) -> float:
    return parse_amount(raw_text)


def validate_required_name(raw_text: str) -> str:
    name = raw_text.strip()
    if not name:
        raise ValueError("Nombre no válido.")
    return name
