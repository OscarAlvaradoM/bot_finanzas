from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import OPCIONES_DEUDORES
from domain.rules import FIXED_GROUP_MEMBERS, PAYMENT_METHOD_OWNER


def build_name_keyboard(names: list[str], include_other: bool = False) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(name, callback_data=name)] for name in names]
    if include_other:
        keyboard.append([InlineKeyboardButton("Otro", callback_data="Otro")])
    return InlineKeyboardMarkup(keyboard)


def build_deudores_keyboard(
    pagador: str,
    selected_deudores: list[str],
    show_done: bool,
) -> InlineKeyboardMarkup:
    nombres_disponibles = [
        name for name in OPCIONES_DEUDORES
        if name not in selected_deudores and name != pagador
    ]

    keyboard = [[InlineKeyboardButton(name, callback_data=name)] for name in nombres_disponibles]

    fixed_group_available = set(FIXED_GROUP_MEMBERS).isdisjoint(set(selected_deudores))
    extra_row = []
    if fixed_group_available:
        extra_row.append(InlineKeyboardButton("Los 4", callback_data="Los 4 de siempre"))
    extra_row.append(InlineKeyboardButton("Otro", callback_data="Otro"))
    if show_done:
        extra_row.append(InlineKeyboardButton("Listo", callback_data="Listo"))

    keyboard.append(extra_row)
    return InlineKeyboardMarkup(keyboard)


def build_include_pagador_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Sí ✅", callback_data="si")],
            [InlineKeyboardButton("No ❌", callback_data="no")],
        ]
    )


def build_payment_method_keyboard(metodos: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(method, callback_data=method)] for method in metodos]
    )


def should_ask_payment_method(pagador: str) -> bool:
    return pagador == PAYMENT_METHOD_OWNER
