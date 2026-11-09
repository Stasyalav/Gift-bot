"""Создание бота и обработчики сообщений.

На этапе 2 бот просто повторяет текст — так мы проверяем, что Long Poll
работает. Настоящий сценарий появится в `handlers.py`.
"""

from __future__ import annotations

import logging

from vkbottle.bot import Bot, Message

from app.config import Config

logger = logging.getLogger(__name__)


def create_bot(config: Config) -> Bot:
    bot = Bot(token=config.vk_token)

    @bot.on.message()
    async def echo(message: Message) -> None:
        text = (message.text or "").strip()
        logger.info("Сообщение от %s: %r", message.from_id, text)

        if not text:
            await message.answer("Пока я умею только повторять текст 🙂")
            return

        await message.answer(f"Эхо: {text}")

    return bot


def run_bot(config: Config) -> None:
    bot = create_bot(config)
    logger.info("Бот запущен для сообщества %s", config.vk_group_id)
    bot.run()
