"""Логика шага «расскажите о получателе и бюджете».

Вынесена из обработчиков, чтобы её можно было проверить без ВК и без
GigaChat. Функция не отправляет сообщения — только обновляет состояние
и говорит, чего не хватает.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.budget import extract_budget, extract_budget_reply, is_bare_budget
from app.states import UserState

BriefAction = Literal["need_brief", "need_budget", "ready"]


@dataclass
class BriefPlan:
    """Что делать после очередного сообщения с описанием."""

    action: BriefAction
    budget_rub: int | None = None
    capped: bool = False
    reused_budget: bool = False


def _merge(existing: str | None, text: str) -> str:
    """Дополняет описание новым сообщением, не дублируя его."""

    text = text.strip()
    if not existing:
        return text
    if not text:
        return existing
    if text.casefold() in existing.casefold():
        return existing
    return f"{existing}\n{text}"


def plan_brief(
    state: UserState,
    text: str,
    *,
    max_budget_rub: int | None = None,
) -> BriefPlan:
    """Разбирает сообщение и решает, можно ли уже собирать подборку.

    Бюджет и описание можно присылать по частям: сначала рассказ о
    получателе, потом сумму, или наоборот.
    """

    text = text.strip()
    budget = extract_budget(text)
    bare = is_bare_budget(text)
    if budget is None and bare:
        budget = extract_budget_reply(text)

    capped = False
    if budget is not None and max_budget_rub is not None and budget > max_budget_rub:
        budget = max_budget_rub
        capped = True

    # Прислали только сумму, а описания ещё нет.
    if bare and not state.brief:
        if budget is None:
            return BriefPlan("need_budget")
        state.budget_rub = budget
        return BriefPlan("need_brief", budget_rub=budget, capped=capped)

    if budget is None:
        state.brief = _merge(state.brief, text)
        # Бюджет уже называли раньше — не заставляем повторять.
        if state.budget_rub is not None:
            return BriefPlan(
                "ready",
                budget_rub=state.budget_rub,
                reused_budget=True,
            )
        return BriefPlan("need_budget")

    state.brief = state.brief if (bare and state.brief) else _merge(state.brief, text)
    state.budget_rub = budget
    return BriefPlan("ready", budget_rub=budget, capped=capped)
