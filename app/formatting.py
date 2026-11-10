"""Сборка текста для ВКонтакте.

ВК не понимает Markdown, поэтому сообщение — обычный текст с переносами
строк. Формат собирается в коде, а не моделью.
"""

from __future__ import annotations

from app.budget import format_rub
from app.schemas import Gift

PRICE_DISCLAIMER = (
    "Цены — ориентировочные: они могут меняться, а наличие в магазинах "
    "стоит уточнить. Ссылки на товары я не даю — идеи можно найти "
    "по названию."
)


def format_price_range(price_min: int, price_max: int) -> str:
    if price_min == price_max:
        return format_rub(price_min)
    return f"{format_rub(price_min)} – {format_rub(price_max)}"


def format_gifts(
    gifts: list[Gift],
    budget_rub: int,
    *,
    intro: str | None = None,
) -> str:
    """Собирает одно сообщение с пятью идеями и дисклеймером."""

    lines: list[str] = [
        intro or f"Вот 5 идей подарка до {format_rub(budget_rub)}:",
        "",
    ]

    for index, gift in enumerate(gifts, start=1):
        lines.append(f"{index}. {gift.name}")
        lines.append(f"Почему подойдёт: {gift.why}")
        lines.append(
            f"Примерная цена: {format_price_range(gift.price_min, gift.price_max)}"
        )
        lines.append(f"Где искать: {gift.category}")
        lines.append("")

    lines.append(PRICE_DISCLAIMER)
    return "\n".join(lines).strip()


def split_for_vk(text: str, limit: int = 4000) -> list[str]:
    """Делит длинный текст на части по границам строк.

    ВК ограничивает сообщение 4096 символами. Оставляем запас, чтобы
    служебные символы не привели к отказу.
    """

    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in text.splitlines():
        line_len = len(line) + 1
        if current and current_len + line_len > limit:
            parts.append("\n".join(current).strip())
            current = []
            current_len = 0
        if line_len > limit:
            # Очень длинная строка — режем принудительно.
            if current:
                parts.append("\n".join(current).strip())
                current = []
                current_len = 0
            for start in range(0, len(line), limit):
                parts.append(line[start : start + limit])
            continue
        current.append(line)
        current_len += line_len

    if current:
        parts.append("\n".join(current).strip())

    return [part for part in parts if part]
