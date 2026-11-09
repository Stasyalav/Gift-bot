"""Приветственные картинки: выбор без повтора и загрузка в ВК.

Картинки лежат в `assets/greetings/`. При первом показе файл загружается
в ВК, а полученный attachment кэшируется в памяти — чтобы не загружать
одну и ту же картинку каждый раз.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path

from vkbottle import API
from vkbottle.tools import PhotoMessageUploader

logger = logging.getLogger(__name__)

GREETINGS_DIR = Path(__file__).resolve().parent.parent / "assets" / "greetings"
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class GreetingImages:
    def __init__(self, api: API) -> None:
        self._uploader = PhotoMessageUploader(api)
        self._cache: dict[Path, str] = {}
        self._files = sorted(
            path
            for path in GREETINGS_DIR.glob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        )
        if not self._files:
            logger.warning("В %s нет картинок — приветствие будет без картинки", GREETINGS_DIR)

    def pick(self, last_name: str | None = None) -> Path | None:
        """Выбирает случайную картинку, не повторяя предыдущую."""

        if not self._files:
            return None
        if len(self._files) == 1:
            return self._files[0]
        candidates = [path for path in self._files if path.name != last_name]
        return random.choice(candidates or self._files)

    async def upload(self, path: Path | None, peer_id: int) -> str | None:
        """Загружает картинку в ВК и возвращает attachment. Ошибки не роняют бота."""

        if path is None:
            return None
        if path in self._cache:
            return self._cache[path]
        try:
            attachment = await self._uploader.upload(str(path), peer_id=peer_id)
        except Exception as exc:  # noqa: BLE001 — картинка не должна ломать диалог
            logger.warning("Не удалось загрузить картинку %s: %s", path.name, exc)
            return None
        self._cache[path] = attachment
        return attachment
