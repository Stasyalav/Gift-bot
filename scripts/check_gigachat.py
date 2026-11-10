"""Проверка доступа к GigaChat.

Запуск:
    .\\.venv\\Scripts\\python.exe scripts\\check_gigachat.py

Скрипт проверяет ключ, сертификат и список доступных моделей. Он не
генерирует подборку — для этого есть scripts/try_ai.py.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from gigachat import GigaChat  # noqa: E402
from gigachat.exceptions import (  # noqa: E402
    AuthenticationError,
    ForbiddenError,
    GigaChatException,
)

from app.config import (  # noqa: E402
    ConfigError,
    load_config,
    require_gigachat_credentials,
)


async def main() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Ошибка настроек: {exc}")
        return 1

    try:
        credentials = require_gigachat_credentials(config)
    except ConfigError as exc:
        print(f"Ошибка настроек: {exc}")
        print()
        print("Откройте .env и заполните GIGACHAT_CREDENTIALS.")
        print("Ключ берётся в личном кабинете developers.sber.ru.")
        return 1

    ca_bundle = config.gigachat_ca_bundle_file
    if not ca_bundle.exists():
        print(f"Не найден сертификат: {ca_bundle}")
        print()
        print("Скачайте корневой сертификат Минцифры в формате PEM:")
        print("  https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt")
        print(f"И сохраните его как {ca_bundle}.")
        print("Подробная инструкция — в certs/README.md.")
        return 1

    if b"-----BEGIN CERTIFICATE-----" not in ca_bundle.read_bytes()[:512]:
        print(f"Файл {ca_bundle} не похож на PEM-сертификат.")
        print("Первая строка должна быть: -----BEGIN CERTIFICATE-----")
        print("Скачайте PEM-версию:")
        print("  https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt")
        return 1

    print(f"Модель: {config.gigachat_model}")
    print(f"Scope: {config.gigachat_scope}")
    print(f"Сертификат: {ca_bundle}")
    print("Проверяю доступ к GigaChat…")

    try:
        async with GigaChat(
            credentials=credentials,
            scope=config.gigachat_scope,
            model=config.gigachat_model,
            ca_bundle_file=str(ca_bundle),
            timeout=config.gigachat_timeout_seconds,
        ) as client:
            models = await client.aget_models()
    except AuthenticationError:
        print("Ошибка: GigaChat не принял ключ. Проверьте GIGACHAT_CREDENTIALS.")
        return 1
    except ForbiddenError:
        print(
            "Ошибка: ключу недоступна выбранная модель или scope. "
            "Проверьте GIGACHAT_SCOPE и GIGACHAT_MODEL."
        )
        return 1
    except GigaChatException as exc:
        print(f"Ошибка GigaChat: {type(exc).__name__}: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 — показываем причину человеку
        print(f"Ошибка соединения: {type(exc).__name__}: {exc}")
        print()
        print("Если это ошибка TLS/сертификата — проверьте, что файл")
        print("certs/russian_trusted_root_ca.cer скачан с gosuslugi.ru/crt.")
        return 1

    model_ids = [model.id_ for model in models.data]
    print("Доступные модели:")
    for model_id in model_ids:
        print(f"- {model_id}")

    if config.gigachat_model not in model_ids:
        print()
        print(
            f"Внимание: модели {config.gigachat_model} нет в списке. "
            "Укажите в GIGACHAT_MODEL одну из доступных."
        )
        return 1

    print()
    print("OK: ключ, сертификат и модель работают.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
