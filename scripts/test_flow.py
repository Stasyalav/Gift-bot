"""Офлайн-проверка связки диалога и AI без ВК и без сети.

Запуск:
    .\\.venv\\Scripts\\python.exe scripts\\test_flow.py
"""

from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.ai import AIError  # noqa: E402
from app.handlers import (  # noqa: E402
    BUDGET_QUESTION,
    _generate,
    _handle_brief,
)
from app.schemas import Gift  # noqa: E402
from app.states import AWAITING_BRIEF, RESULTS, UserState  # noqa: E402

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  OK  {name}")
        return
    failures.append(name)
    print(f"  FAIL {name}" + (f" — {detail}" if detail else ""))


class FakeMessage:
    from_id = 1
    peer_id = 1

    def __init__(self) -> None:
        self.answers: list[tuple[str, dict[str, object]]] = []

    async def answer(self, text: str, **kwargs: object) -> None:
        self.answers.append((text, kwargs))


class FakeAI:
    def __init__(self, gifts: list[Gift] | None = None, error: Exception | None = None):
        self._gifts = gifts or []
        self._error = error
        self.calls: list[tuple[str, int, list[str] | None]] = []

    async def suggest(
        self,
        brief: str,
        budget_rub: int,
        *,
        avoid_names: list[str] | None = None,
    ) -> list[Gift]:
        self.calls.append((brief, budget_rub, avoid_names))
        if self._error is not None:
            raise self._error
        return self._gifts


def make_gifts() -> list[Gift]:
    return [
        Gift(
            name=f"Идея {index}",
            why="Подойдёт, потому что учитывает увлечения получателя.",
            price_min=500 * index,
            price_max=1000 * index,
            category="маркетплейсы",
        )
        for index in range(1, 6)
    ]


async def test_generation() -> None:
    print("Успешная генерация")
    state = UserState(brief="Маме, любит книги", budget_rub=5000)
    message = FakeMessage()
    ai = FakeAI(make_gifts())

    await _generate(message, state, ai, 5000)  # type: ignore[arg-type]

    check("AI вызван один раз", len(ai.calls) == 1, str(ai.calls))
    check("бюджет передан", ai.calls[0][1] == 5000, str(ai.calls[0][1]))
    check("состояние результатов", state.stage == RESULTS, state.stage)
    check("запомнены названия", len(state.last_gifts) == 5, str(state.last_gifts))
    check("есть сообщение с подборкой", any("Идея 5" in text for text, _ in message.answers))
    last_text, last_kwargs = message.answers[-1]
    check("клавиатура на последнем сообщении", "keyboard" in last_kwargs)
    check("дисклеймер в тексте", "ориентировочные" in last_text)


async def test_generation_with_avoid() -> None:
    print("Другая подборка не повторяет прошлые идеи")
    state = UserState(brief="Маме, любит книги", budget_rub=5000)
    state.last_gifts = ["Идея 1", "Идея 2"]
    message = FakeMessage()
    ai = FakeAI(make_gifts())

    await _generate(message, state, ai, 5000, avoid_names=state.last_gifts)  # type: ignore[arg-type]

    check("прошлые идеи переданы", ai.calls[0][2] == ["Идея 1", "Идея 2"])
    check("вступление про другие идеи", "ещё 5 идей" in message.answers[-1][0])


async def test_ai_error() -> None:
    print("Ошибка AI не роняет диалог")
    state = UserState(brief="Маме, любит книги", budget_rub=5000)
    message = FakeMessage()
    ai = FakeAI(error=AIError("GigaChat временно недоступен"))

    await _generate(message, state, ai, 5000)  # type: ignore[arg-type]

    check("состояние результатов", state.stage == RESULTS, state.stage)
    check("понятный текст ошибки", "временно недоступен" in message.answers[-1][0])
    check("кнопка повтора", "keyboard" in message.answers[-1][1])


async def test_brief_without_budget() -> None:
    print("Без бюджета подборка не запускается")
    state = UserState()
    message = FakeMessage()
    ai = FakeAI(make_gifts())
    config = SimpleNamespace(max_budget_rub=None)

    await _handle_brief(message, state, ai, config, "Маме, любит книги")  # type: ignore[arg-type]

    check("спросили бюджет", message.answers[-1][0] == BUDGET_QUESTION)
    check("AI не вызывался", not ai.calls)
    check("описание сохранено", state.brief == "Маме, любит книги", state.brief or "")


async def test_brief_with_budget() -> None:
    print("Бюджет в тексте запускает подборку")
    state = UserState()
    message = FakeMessage()
    ai = FakeAI(make_gifts())
    config = SimpleNamespace(max_budget_rub=None)

    await _handle_brief(
        message,
        state,
        ai,
        config,
        "Маме, любит книги, до 5 000 ₽",
    )  # type: ignore[arg-type]

    check("AI вызван", len(ai.calls) == 1, str(ai.calls))
    check("бюджет 5000", ai.calls[0][1] == 5000, str(ai.calls[0][1]))
    check("состояние результатов", state.stage == RESULTS, state.stage)


async def test_no_ai() -> None:
    print("Без ключа AI бот честно сообщает")
    state = UserState(brief="Маме, любит книги", budget_rub=5000)
    message = FakeMessage()

    await _generate(message, state, None, 5000)  # type: ignore[arg-type]

    check("сообщение о настройке", "не настроен" in message.answers[-1][0])
    check("вернулись к описанию", state.stage == AWAITING_BRIEF, state.stage)


async def main() -> int:
    await test_generation()
    await test_generation_with_avoid()
    await test_ai_error()
    await test_brief_without_budget()
    await test_brief_with_budget()
    await test_no_ai()

    print()
    if failures:
        print(f"Провалено проверок: {len(failures)}")
        for name in failures:
            print(f"- {name}")
        return 1
    print("Все проверки связки пройдены.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
