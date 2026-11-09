"""Создание бота и запуск Long Poll."""

from __future__ import annotations

import logging

from vkbottle.bot import Bot

from app.config import Config
from app.handlers import register_handlers
from app.images import GreetingImages

logger = logging.getLogger(__name__)


def create_bot(config: Config) -> Bot:
    bot = Bot(token=config.vk_token)
    images = GreetingImages(bot.api)
    register_handlers(bot, config, images)
    return bot


def run_bot(config: Config) -> None:
    bot = create_bot(config)
    logger.info("Бот запущен для сообщества %s", config.vk_group_id)
    bot.run()
