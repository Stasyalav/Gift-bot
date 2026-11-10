"""Извлечение бюджета из свободного текста.

Бюджет — обязательное условие подборки, поэтому его нужно найти в сообщении
пользователя. Делаем это простыми регулярками: они покрывают обычные
формулировки и не пытаются угадать то, чего в тексте нет.
"""

from __future__ import annotations

import re

_NUMBER = r"(?:\d{1,3}(?:[ \u00a0]\d{3})+|\d+)"
_CURRENCY = r"(?:₽|руб(?:\.|лей|ля|ль)?|р\.|р\b)"
_THOUSANDS = r"(?:к|тыс\.?|тысяч[а-я]*)"

# Диапазон: «5000–7000 ₽» — берём верхнюю границу.
_RANGE_RE = re.compile(
    rf"({_NUMBER})\s*[-–—]\s*({_NUMBER})\s*{_CURRENCY}",
    re.IGNORECASE,
)

# Явный бюджет: «до 5000», «не больше 3 000», «бюджет 5000».
_EXPLICIT_RE = re.compile(
    rf"(?:до|не более|не больше|максимум|в пределах|бюджет[^\d]{{0,25}}|"
    rf"потратить[^\d]{{0,25}})\s*({_NUMBER})\s*({_THOUSANDS})?",
    re.IGNORECASE,
)

# Число с валютой: «5000 ₽», «3 000 рублей».
_CURRENCY_RE = re.compile(
    rf"({_NUMBER})\s*{_CURRENCY}",
    re.IGNORECASE,
)

# Число с «к»/«тыс»: «5к», «7 тысяч».
_THOUSANDS_RE = re.compile(
    rf"(\d+(?:[.,]\d+)?)\s*{_THOUSANDS}\b",
    re.IGNORECASE,
)

MIN_BUDGET_RUB = 100
MAX_BUDGET_RUB = 10_000_000


def _to_int(raw: str, *, thousands: bool = False) -> int | None:
    cleaned = re.sub(r"[^\d,.]", "", raw).replace(",", ".")
    if not cleaned:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if thousands:
        value *= 1000
    return int(round(value))


def _valid(value: int | None) -> int | None:
    if value is None:
        return None
    if MIN_BUDGET_RUB <= value <= MAX_BUDGET_RUB:
        return value
    return None


def _last_valid(matches: list[int | None]) -> int | None:
    for value in reversed(matches):
        if value is not None:
            return value
    return None


def extract_budget(text: str) -> int | None:
    """Возвращает бюджет в рублях или None, если он не назван.

    Приоритет: диапазон, затем явная формулировка («до …», «бюджет …»),
    затем число с валютой, затем число с «к»/«тыс».
    """

    if not text:
        return None

    normalized = text.replace("\u00a0", " ").lower()

    range_values = [
        _valid(_to_int(match.group(2)))
        for match in _RANGE_RE.finditer(normalized)
    ]
    value = _last_valid(range_values)
    if value is not None:
        return value

    explicit_values = [
        _valid(
            _to_int(
                match.group(1),
                thousands=bool(match.group(2)),
            )
        )
        for match in _EXPLICIT_RE.finditer(normalized)
    ]
    value = _last_valid(explicit_values)
    if value is not None:
        return value

    currency_values = [
        _valid(_to_int(match.group(1)))
        for match in _CURRENCY_RE.finditer(normalized)
    ]
    value = _last_valid(currency_values)
    if value is not None:
        return value

    thousands_values = [
        _valid(_to_int(match.group(1), thousands=True))
        for match in _THOUSANDS_RE.finditer(normalized)
    ]
    return _last_valid(thousands_values)


def format_rub(value: int) -> str:
    """Форматирует сумму в рублях: 5000 -> «5 000 ₽»."""

    return f"{value:,}".replace(",", " ") + " ₽"
