"""Офлайн-проверка диалога: бюджет и описание по частям.

Запуск:
    .\\.venv\\Scripts\\python.exe scripts\\test_dialogue.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.budget import extract_budget, extract_budget_reply, is_bare_budget  # noqa: E402
from app.dialogue import plan_brief  # noqa: E402
from app.keyboards import results_keyboard, retry_keyboard  # noqa: E402
from app.states import UserState  # noqa: E402

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  OK  {name}")
        return
    failures.append(name)
    print(f"  FAIL {name}" + (f" — {detail}" if detail else ""))


def test_full_brief() -> None:
    print("Полное описание сразу")
    state = UserState()
    plan = plan_brief(
        state,
        "Маме на день рождения, любит уют и книги, до 5 000 ₽",
    )
    check("можно собирать", plan.action == "ready", plan.action)
    check("бюджет 5000", plan.budget_rub == 5000, str(plan.budget_rub))
    check("описание сохранено", "уют" in (state.brief or ""))


def test_budget_second() -> None:
    print("Сначала описание, потом бюджет")
    state = UserState()
    plan = plan_brief(state, "Маме на день рождения, любит уют и книги")
    check("просим бюджет", plan.action == "need_budget", plan.action)
    check("описание сохранено", "книги" in (state.brief or ""))

    plan = plan_brief(state, "5000")
    check("короткий ответ понят", plan.action == "ready", plan.action)
    check("бюджет 5000", plan.budget_rub == 5000, str(plan.budget_rub))
    check("описание не затёрто", "книги" in (state.brief or ""), state.brief or "")
    check("не считаем, что бюджет был раньше", not plan.reused_budget)


def test_budget_first() -> None:
    print("Сначала бюджет, потом описание")
    state = UserState()
    plan = plan_brief(state, "5к")
    check("просим описание", plan.action == "need_brief", plan.action)
    check("бюджет 5000", plan.budget_rub == 5000, str(plan.budget_rub))

    plan = plan_brief(state, "Коллеге на новоселье, любит растения")
    check("можно собирать", plan.action == "ready", plan.action)
    check("бюджет сохранён", plan.budget_rub == 5000, str(plan.budget_rub))
    check("описание сохранено", "растения" in (state.brief or ""))


def test_edit_reuses_budget() -> None:
    print("Изменение критериев сохраняет бюджет")
    state = UserState(brief="Старое описание", budget_rub=4000)
    plan = plan_brief(state, "Другу на 30 лет, любит музыку")
    check("можно собирать", plan.action == "ready", plan.action)
    check("бюджет прежний", plan.budget_rub == 4000, str(plan.budget_rub))
    check("пометка о переиспользовании", plan.reused_budget)
    check("новое описание", "музыку" in (state.brief or ""), state.brief or "")


def test_new_budget_wins() -> None:
    print("Новый бюджет в тексте важнее прежнего")
    state = UserState(brief="Старое описание", budget_rub=4000)
    plan = plan_brief(state, "То же самое, но до 7 000 ₽")
    check("бюджет 7000", plan.budget_rub == 7000, str(plan.budget_rub))
    check("без пометки переиспользования", not plan.reused_budget)


def test_max_cap() -> None:
    print("Ограничение максимального бюджета")
    state = UserState()
    plan = plan_brief(state, "До 50 000 ₽, подарок другу", max_budget_rub=10_000)
    check("бюджет урезан", plan.budget_rub == 10_000, str(plan.budget_rub))
    check("есть пометка", plan.capped)


def test_bare_detection() -> None:
    print("Определение короткого ответа с суммой")
    check("«5000» — только сумма", is_bare_budget("5000"))
    check("«до 5 000 ₽» — только сумма", is_bare_budget("до 5 000 ₽"))
    check("«5к» — только сумма", is_bare_budget("5к"))
    check("описание — не только сумма", not is_bare_budget("Маме до 5000"))
    check("«5000» разбирается", extract_budget_reply("5000") == 5000)
    check("«3 тысячи» разбирается", extract_budget_reply("3 тысячи") == 3000)
    check("обычный текст не разбирается", extract_budget_reply("маме") is None)


def test_budget_variants() -> None:
    print("Разные формулировки бюджета")
    cases = {
        "до 5000": 5000,
        "не больше 3 000 ₽": 3000,
        "бюджет 7000 рублей": 7000,
        "5к": 5000,
        "7 тысяч": 7000,
        "5000-7000 ₽": 7000,
        "потратить до 2 500": 2500,
    }
    for text, expected in cases.items():
        check(f"«{text}»", extract_budget(text) == expected, str(extract_budget(text)))


def test_keyboards() -> None:
    print("Кнопки под результатом и ошибкой")
    results = json.loads(results_keyboard())
    commands = [
        button["action"]["payload"]["cmd"]
        for row in results["buttons"]
        for button in row
    ]
    check("другая подборка", "more" in commands, str(commands))
    check("изменить критерии", "edit" in commands, str(commands))
    check("начать заново", "restart" in commands, str(commands))

    retry = json.loads(retry_keyboard())
    retry_commands = [
        button["action"]["payload"]["cmd"]
        for row in retry["buttons"]
        for button in row
    ]
    check("повторить", "retry" in retry_commands, str(retry_commands))


def main() -> int:
    test_full_brief()
    test_budget_second()
    test_budget_first()
    test_edit_reuses_budget()
    test_new_budget_wins()
    test_max_cap()
    test_bare_detection()
    test_budget_variants()
    test_keyboards()

    print()
    if failures:
        print(f"Провалено проверок: {len(failures)}")
        for name in failures:
            print(f"- {name}")
        return 1
    print("Все проверки диалога пройдены.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
