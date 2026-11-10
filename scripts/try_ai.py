"""Проверка подбора подарков в терминале, без ВК.

Запуск:
    .\\.venv\\Scripts\\python.exe scripts\\try_ai.py "Маме на день рождения, любит уют и книги" --budget 5000

Если --budget не указан, бюджет ищется в тексте описания.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.ai import AIError, GiftAI  # noqa: E402
from app.budget import extract_budget, format_rub  # noqa: E402
from app.config import ConfigError, load_config  # noqa: E402
from app.formatting import format_gifts  # noqa: E402

DEFAULT_BRIEF = (
    "Маме на день рождения, 55 лет. Любит уют, книги, чай и спокойные "
    "вечера. Не любит громкие вечеринки и сладкое."
)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Тест подбора подарков через GigaChat")
    parser.add_argument(
        "brief",
        nargs="?",
        default=DEFAULT_BRIEF,
        help="Описание получателя и повода",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=None,
        help="Бюджет в рублях. Если не указан — ищется в тексте.",
    )
    args = parser.parse_args()

    budget = args.budget if args.budget is not None else extract_budget(args.brief)
    if budget is None:
        print("Не удалось определить бюджет. Укажите его явно: --budget 5000")
        return 1

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Ошибка настроек: {exc}")
        return 1

    print(f"Бюджет: {format_rub(budget)}")
    print(f"Описание: {args.brief}")
    print("Запрашиваю подборку у GigaChat…")
    print()

    try:
        ai = GiftAI(config)
    except ConfigError as exc:
        print(f"Ошибка настроек: {exc}")
        return 1

    started = time.perf_counter()
    try:
        gifts = await ai.suggest(args.brief, budget)
    except AIError as exc:
        print(f"Ошибка AI: {exc}")
        return 1
    finally:
        await ai.aclose()
    elapsed = time.perf_counter() - started

    print(format_gifts(gifts, budget))
    print()
    print("—" * 40)
    max_price = max(gift.price_max for gift in gifts)
    print(f"Проверка: {len(gifts)} идей, максимальная цена {format_rub(max_price)}.")
    print(f"Бюджет {format_rub(budget)}: {'соблюдён' if max_price <= budget else 'НАРУШЕН'}.")
    print(f"Время запроса: {elapsed:.1f} с.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
