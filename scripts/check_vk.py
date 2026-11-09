"""Проверка подключения к ВКонтакте.

Скрипт ничего не пишет в сообщество: он только спрашивает у ВК права
токена, данные сообщества и настройки Long Poll.

Запуск:
    .\\.venv\\Scripts\\python.exe scripts\\check_vk.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from vkbottle import API  # noqa: E402

from app.config import ConfigError, load_config  # noqa: E402


async def check() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"❌ Ошибка настроек: {exc}")
        return 1

    api = API(config.vk_token)
    ok = True

    print("1/4 Права токена...")
    try:
        permissions = await api.groups.get_token_permissions()
        names = {item.name for item in (permissions.permissions or [])}
        print(f"    есть: {', '.join(sorted(names)) or '—'}")
        missing = {"messages", "photos"} - names
        if missing:
            print(f"    ❌ не хватает прав: {', '.join(sorted(missing))}")
            ok = False
        else:
            print("    ✅ «Сообщения сообщества» и «Фотографии» на месте")
    except Exception as exc:  # noqa: BLE001 — хотим показать любую ошибку
        print(f"    ❌ {exc}")
        return 1

    print("2/4 Сообщество...")
    try:
        result = await api.groups.get_by_id(group_ids=[config.vk_group_id])
        if not result.groups:
            print("    ❌ сообщество не найдено — проверьте VK_GROUP_ID")
            ok = False
        else:
            group = result.groups[0]
            print(f"    ✅ {group.name} (id {group.id})")
    except Exception as exc:  # noqa: BLE001
        print(f"    ❌ {exc}")
        ok = False

    print("3/4 Long Poll...")
    try:
        server = await api.messages.get_long_poll_server(
            group_id=config.vk_group_id, lp_version=3
        )
        print(f"    ✅ доступен (ts={server.ts})")
    except Exception as exc:  # noqa: BLE001
        print(f"    ❌ {exc}")
        ok = False

    print("4/4 Событие message_new...")
    try:
        settings = await api.groups.get_long_poll_settings(group_id=config.vk_group_id)
        if settings.events and settings.events.message_new:
            print(f"    ✅ включено (API {settings.api_version})")
        else:
            print("    ❌ выключено — включите «Входящие сообщения» в Long Poll")
            ok = False
    except Exception as exc:  # noqa: BLE001
        print(f"    ❌ {exc}")
        ok = False

    print()
    if ok:
        print("✅ Всё готово. Запуск бота: python run.py")
        return 0

    print("❌ Есть проблемы — смотрите пункты выше.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(check()))
