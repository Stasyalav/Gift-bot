"""Состояние диалога с пользователем.

Для MVP состояние хранится в памяти: перезапустили бота — диалог
начинается заново. Это осознанное решение, чтобы не тащить базу данных
на старте.
"""

from __future__ import annotations

from dataclasses import dataclass, field

IDLE = "idle"
AWAITING_BRIEF = "awaiting_brief"
AWAITING_ANSWER = "awaiting_answer"
RESULTS = "results"


@dataclass
class UserState:
    stage: str = IDLE
    brief: str | None = None
    budget_rub: int | None = None
    last_image: str | None = None
    last_gifts: list[str] = field(default_factory=list)


_states: dict[int, UserState] = {}


def get_state(user_id: int) -> UserState:
    """Возвращает состояние пользователя, создавая его при первом обращении."""

    return _states.setdefault(user_id, UserState())


def reset_state(user_id: int) -> UserState:
    """Сбрасывает диалог пользователя."""

    _states[user_id] = UserState()
    return _states[user_id]
