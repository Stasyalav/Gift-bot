"""Обработчики сообщений.

Этап 3: приветствие, подсказки и клавиатуры. Подбор подарков появится
на следующем этапе, когда подключим AI.
"""

from __future__ import annotations

import json
import logging

from vkbottle.bot import Bot, Message

from app.config import Config
from app.images import GreetingImages
from app.keyboards import help_keyboard, start_keyboard
from app.states import AWAITING_BRIEF, IDLE, UserState, get_state

logger = logging.getLogger(__name__)

GREETING_TEXT = (
    "Добрый день 🌸\n"
    "Я помогу подобрать подарок — бережно, с вниманием к деталям и вашему бюджету.\n\n"
    "Чтобы подборка получилась точной, расскажите хотя бы немного:\n"
    "• пол и возраст\n"
    "• кто это — мама, друг, коллега…\n"
    "• повод\n"
    "• увлечения\n"
    "• что любит и что не любит\n"
    "• бюджет — до какой суммы\n"
    "• всё остальное, что важно\n\n"
    "Можно писать свободно и не по порядку. Обязателен только бюджет 🙂"
)

HELP_TEXT = (
    "Это просто:\n"
    "1. Вы рассказываете, кому и на какой повод ищете подарок.\n"
    "2. Я предлагаю 5 идей с примерными ценами и объяснением, почему они подойдут.\n"
    "3. Можно попросить другую подборку или изменить бюджет.\n\n"
    "Обязательное условие — назвать бюджет, хотя бы примерно. Например:\n"
    "«Маме на день рождения, любит уют и книги, до 5 000 ₽»."
)

THANKS_TEXT = (
    "Спасибо! Описание сохранил 🌸\n"
    "Подбор идей я подключу на следующем этапе — осталось совсем немного."
)

START_WORDS = {"/start", "начать", "start", "привет", "меню"}
HELP_WORDS = {"как это работает", "помощь", "help"}


def _payload_command(message: Message) -> str | None:
    payload = message.payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None
    if isinstance(payload, dict):
        command = payload.get("cmd")
        return str(command) if command else None
    return None


async def _send_greeting(
    message: Message, state: UserState, images: GreetingImages
) -> None:
    state.stage = AWAITING_BRIEF
    path = images.pick(state.last_image)
    attachment = await images.upload(path, message.peer_id)
    if path is not None:
        state.last_image = path.name

    await message.answer(
        GREETING_TEXT,
        attachment=attachment,
        keyboard=start_keyboard(),
    )


def register_handlers(bot: Bot, config: Config, images: GreetingImages) -> None:
    @bot.on.message()
    async def handle_message(message: Message) -> None:
        text = (message.text or "").strip()
        lowered = text.lower()
        command = _payload_command(message)
        state = get_state(message.from_id)

        logger.info(
            "Сообщение от %s: %r (stage=%s, cmd=%s)",
            message.from_id,
            text,
            state.stage,
            command,
        )

        if command == "help" or lowered in HELP_WORDS:
            await message.answer(HELP_TEXT, keyboard=help_keyboard())
            return

        if command == "start" or lowered in START_WORDS or state.stage == IDLE:
            await _send_greeting(message, state, images)
            return

        if state.stage == AWAITING_BRIEF:
            state.brief = text
            await message.answer(THANKS_TEXT, keyboard=help_keyboard())
            return

        await _send_greeting(message, state, images)
