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


def results_keyboard() -> str:
    """Клавиатура под готовой подборкой."""

    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(
        Text("🔄 Другая подборка", payload={"cmd": "more"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    keyboard.row()
    keyboard.add(
        Text("✏️ Изменить критерии", payload={"cmd": "edit"}),
        color=KeyboardButtonColor.SECONDARY,
    )
    keyboard.row()
    keyboard.add(
        Text("🏠 Начать заново", payload={"cmd": "restart"}),
        color=KeyboardButtonColor.SECONDARY,
    )
    return keyboard.get_json()


def retry_keyboard() -> str:
    """Клавиатура, если AI не смог собрать подборку."""

    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(
        Text("🔄 Попробовать ещё раз", payload={"cmd": "retry"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    keyboard.row()
    keyboard.add(
        Text("✏️ Изменить критерии", payload={"cmd": "edit"}),
        color=KeyboardButtonColor.SECONDARY,
    )
    keyboard.row()
    keyboard.add(
        Text("🏠 Начать заново", payload={"cmd": "restart"}),
        color=KeyboardButtonColor.SECONDARY,
    )
    return keyboard.get_json()
