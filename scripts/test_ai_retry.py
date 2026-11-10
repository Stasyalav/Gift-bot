"""Офлайн-проверка повторов и запасного JSON-пути.

GigaChat может вернуть ответ не по схеме или превысить бюджет. Здесь мы
подменяем клиент и проверяем, что код делает вторую попытку, а не отдаёт
плохой результат пользователю.

Запуск:
    .\\.venv\\Scripts\\python.exe scripts\\test_ai_retry.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from gigachat.exceptions import LengthFinishReasonError  # noqa: E402

from app.ai import AIError, GiftAI  # noqa: E402
from app.schemas import Gift, GiftResponse  # noqa: E402


def make_gift(name: str, price_max: int) -> Gift:
    return Gift(
        name=name,
        why="Подойдёт, потому что человек любит уютные и полезные вещи.",
        price_min=max(1, price_max - 500),
        price_max=price_max,
        category="маркетплейсы",
    )


def make_response(prices: list[int]) -> GiftResponse:
    names = ["Плед", "Чай", "Книга", "Свеча", "Подставка"]
    return GiftResponse(
        gifts=[make_gift(name, price) for name, price in zip(names, prices)]
    )


class FakePart:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeMessage:
    def __init__(self, role: str, text: str) -> None:
        self.role = role
        self.content = [FakePart(text)]


class FakeCompletion:
    def __init__(self, text: str) -> None:
        self.messages = [FakeMessage("assistant", text)]
        self.usage = None


class FakeChat:
    """Подменяет client.achat: parse — структурированный путь, create — обычный."""

    def __init__(self, results: list[object]) -> None:
        self.results = list(results)
        self.parse_calls = 0
        self.create_calls = 0

    async def parse(self, payload, *, response_format, strict):
        self.parse_calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        assert isinstance(result, GiftResponse)
        text = json.dumps(result.model_dump(), ensure_ascii=False)
        return FakeCompletion(text), result

    async def create(self, payload):
        self.create_calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        assert isinstance(result, GiftResponse)
        text = json.dumps(result.model_dump(), ensure_ascii=False)
        return FakeCompletion(text)


def make_ai(chat: FakeChat) -> GiftAI:
    ai = GiftAI.__new__(GiftAI)
    ai._client = type("Client", (), {"achat": chat})()  # type: ignore[attr-defined]
    ai._model = "fake"  # type: ignore[attr-defined]
    return ai


async def test_over_budget_then_ok() -> None:
    chat = FakeChat(
        [
            make_response([9000, 9000, 9000, 9000, 9000]),
            make_response([1500, 2000, 1800, 900, 1300]),
        ]
    )
    ai = make_ai(chat)
    gifts = await ai.suggest("Маме, любит уют", 5000)
    assert len(gifts) == 5
    assert max(gift.price_max for gift in gifts) <= 5000
    assert chat.parse_calls == 1
    assert chat.create_calls == 1
    print("  ok: превышение бюджета -> повтор обычным JSON -> корректный ответ")


async def test_bad_json_then_ok() -> None:
    chat = FakeChat(
        [
            ValueError("битый JSON"),
            make_response([1500, 2000, 1800, 900, 1300]),
        ]
    )
    ai = make_ai(chat)
    gifts = await ai.suggest("Коллеге, любит кофе", 3000)
    assert len(gifts) == 5
    assert chat.parse_calls == 1
    assert chat.create_calls == 1
    print("  ok: ошибка схемы -> повтор обычным JSON -> корректный ответ")


async def test_length_then_ok() -> None:
    chat = FakeChat(
        [
            LengthFinishReasonError(None),
            make_response([1500, 2000, 1800, 900, 1300]),
        ]
    )
    ai = make_ai(chat)
    gifts = await ai.suggest("Другу, любит музыку", 4000)
    assert len(gifts) == 5
    print("  ok: обрезанный ответ -> повтор -> корректный ответ")


async def test_both_bad() -> None:
    chat = FakeChat([ValueError("плохо"), ValueError("снова плохо")])
    ai = make_ai(chat)
    try:
        await ai.suggest("Кому-то", 1000)
    except AIError as exc:
        assert "не прошёл проверку" in str(exc)
        print("  ok: два плохих ответа -> понятная ошибка AIError")
        return
    raise AssertionError("ожидалась AIError")


async def main() -> int:
    print("Повторы и запасной путь:")
    await test_over_budget_then_ok()
    await test_bad_json_then_ok()
    await test_length_then_ok()
    await test_both_bad()
    print()
    print("OK: повторы работают.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
