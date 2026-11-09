"""Клавиатуры и подписи кнопок."""

from __future__ import annotations

from vkbottle import Keyboard, KeyboardButtonColor, Text


def start_keyboard() -> str:
    """Клавиатура под приветствием."""

    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(
        Text("🎁 Подобрать подарок", payload={"cmd": "start"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    keyboard.add(
        Text("ℹ️ Как это работает", payload={"cmd": "help"}),
        color=KeyboardButtonColor.SECONDARY,
    )
    return keyboard.get_json()


def help_keyboard() -> str:
    """Клавиатура под справкой и промежуточными сообщениями."""

    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(
        Text("🎁 Подобрать подарок", payload={"cmd": "start"}),
        color=KeyboardButtonColor.POSITIVE,
    )
    return keyboard.get_json()
