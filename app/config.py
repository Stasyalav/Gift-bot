"""Настройки приложения.

Все секреты читаются из `.env` в корне проекта. Код никогда не хранит
токены и ключи внутри себя.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


class ConfigError(RuntimeError):
    """Не хватает обязательной настройки или она заполнена неверно."""


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Не задана переменная {name}. "
            "Скопируйте .env.example в .env и заполните её."
        )
    return value


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Config:
    """Проверенные настройки, с которыми работает приложение."""

    vk_token: str
    vk_group_id: int
    gigachat_credentials: str
    gigachat_scope: str
    gigachat_model: str
    gigachat_ca_bundle_file: Path
    log_level: str
    max_budget_rub: int | None


def load_config() -> Config:
    """Читает `.env` и возвращает готовый объект настроек.

    Вызывается один раз при старте приложения. Если чего-то не хватает,
    выбрасывает ConfigError с понятным текстом — чтобы не искать причину
    по невнятной ошибке глубоко в библиотеке.
    """

    group_id_raw = _require("VK_GROUP_ID")
    try:
        group_id = int(group_id_raw)
    except ValueError as exc:
        raise ConfigError("VK_GROUP_ID должен быть числом (только цифры).") from exc

    ca_raw = _optional(
        "GIGACHAT_CA_BUNDLE_FILE", "certs/russian_trusted_root_ca.cer"
    )
    ca_path = Path(ca_raw)
    if not ca_path.is_absolute():
        ca_path = PROJECT_ROOT / ca_path

    max_budget_raw = _optional("MAX_BUDGET_RUB")
    max_budget: int | None = None
    if max_budget_raw:
        try:
            max_budget = int(max_budget_raw)
        except ValueError as exc:
            raise ConfigError("MAX_BUDGET_RUB должен быть целым числом.") from exc

    return Config(
        vk_token=_require("VK_TOKEN"),
        vk_group_id=group_id,
        gigachat_credentials=_require("GIGACHAT_CREDENTIALS"),
        gigachat_scope=_optional("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
        gigachat_model=_optional("GIGACHAT_MODEL", "GigaChat-2"),
        gigachat_ca_bundle_file=ca_path,
        log_level=_optional("LOG_LEVEL", "INFO").upper(),
        max_budget_rub=max_budget,
    )
