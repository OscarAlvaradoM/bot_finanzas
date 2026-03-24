from telegram.ext import ContextTypes


async def finish_callback(query, text: str) -> None:
    await query.edit_message_text(text)


def was_callback_processed(context: ContextTypes.DEFAULT_TYPE, key: str) -> bool:
    return bool(context.user_data.get(key))


def mark_callback_processed(context: ContextTypes.DEFAULT_TYPE, key: str) -> None:
    context.user_data[key] = True
