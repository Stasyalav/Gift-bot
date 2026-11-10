"""Офлайн-проверки схемы, бюджета и форматирования.

Эти тесты не обращаются к GigaChat — они проверяют, что код правильно
отбраковывает плохие ответы модели.

Запуск:
    .\\.venv\\Scripts\\python.exe scripts\\test_ai_validation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pydantic import ValidationError  # noqa: E402

from app.budget import extract_budget  # noqa: E402
from app.formatting import format_gifts, split_for_vk  # noqa: E402
from app.schemas import Gift, GiftResponse  # noqa: E402


def make_gift(
    name: str,
    price_min: int = 1000,
    price_max: int = 1500,
    category: str = "маркетплейсы",
) -> Gift:
    return Gift(
        name=name,
        why="Подойдёт, потому что человек любит уютные и полезные вещи.",
        price_min=price_min,
        price_max=price_max,
        category=category,  # type: ignore[arg-type]
    )


def make_response() -> GiftResponse:
    return GiftResponse(
        gifts=[
            make_gift("Тёплый плед", 1200, 2000),
            make_gift("Набор для чая", 800, 1500),
            make_gift("Книга с иллюстрациями", 900, 1800),
            make_gift("Свеча ручной работы", 500, 900),
            make_gift("Подставка для книг", 700, 1300),
        ]
    )


def expect_error(label: str, func) -> None:
    try:
        func()
    except (ValidationError, ValueError):
        print(f"  ok: {label} — отклонено")
        return
    raise AssertionError(f"{label}: ошибка не была обнаружена")


def test_budget() -> None:
    print("Бюджет:")
    cases = [
        ("до 5000", 5000),
        ("бюджет 3 000 рублей", 3000),
        ("примерно 5к", 5000),
        ("7 тысяч", 7000),
        ("5000–7000 ₽", 7000),
        ("потратить до 12 500 ₽", 12500),
        ("маме 55 лет, любит книги", None),
        ("до 5 лет", None),
        ("совсем без бюджета", None),
    ]
    for text, expected in cases:
        actual = extract_budget(text)
        assert actual == expected, f"{text!r}: ожидалось {expected}, получено {actual}"
        print(f"  ok: {text!r} -> {actual}")


def test_schema() -> None:
    print("Схема:")
    response = make_response()
    assert len(response.gifts) == 5
    print("  ok: 5 идей проходят")

    expect_error(
        "4 идеи",
        lambda: GiftResponse(gifts=make_response().gifts[:4]),
    )
    expect_error(
        "6 идей",
        lambda: GiftResponse(gifts=make_response().gifts + [make_gift("Ещё идея")]),
    )
    expect_error(
        "повтор названий",
        lambda: GiftResponse(
            gifts=make_response().gifts[:4] + [make_gift("Тёплый плед")]
        ),
    )
    expect_error(
        "price_min > price_max",
        lambda: make_gift("Странная цена", 2000, 1000),
    )
    expect_error(
        "недопустимая category",
        lambda: make_gift("Что-то", category="секретный магазин"),
    )


def test_budget_check() -> None:
    print("Проверка бюджета:")
    response = make_response()
    assert response.over_budget(5000) == []
    print("  ok: бюджет 5000 — нарушений нет")

    over = response.over_budget(1000)
    assert len(over) == 4
    print("  ok: бюджет 1000 — найдены 4 нарушения из 5")

    expect_error("check_budget", lambda: response.check_budget(1000))


def test_formatting() -> None:
    print("Форматирование:")
    response = make_response()
    text = format_gifts(response.gifts, 5000)
    assert "1. Тёплый плед" in text
    assert "Цены — ориентировочные" in text
    assert len(text) < 4096
    print(f"  ok: сообщение {len(text)} символов, меньше 4096")

    long_text = "\n".join(f"Строка {index}" for index in range(1000))
    parts = split_for_vk(long_text, limit=1000)
    assert all(len(part) <= 1000 for part in parts)
    assert "\n".join(parts).replace("\n", "") == long_text.replace("\n", "")
    print(f"  ok: длинный текст разбит на {len(parts)} частей")


def main() -> int:
    test_budget()
    test_schema()
    test_budget_check()
    test_formatting()
    print()
    print("OK: все офлайн-проверки прошли.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
