"""Структура ответа AI и проверки, которым мы доверяем больше, чем модели.

GigaChat возвращает данные в формате JSON, а Pydantic проверяет их по схеме.
Но главное — бюджет проверяется отдельно, в коде: модели доверять в этом
вопросе нельзя.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

GiftCategory = Literal[
    "маркетплейсы",
    "рукодельные ярмарки",
    "магазины города",
    "онлайн-магазины",
    "сервисы впечатлений",
    "книжные магазины",
    "магазины для дома и уюта",
    "магазины косметики и ухода",
    "винтажные и блошиные рынки",
]

GIFT_CATEGORIES: tuple[str, ...] = (
    "маркетплейсы",
    "рукодельные ярмарки",
    "магазины города",
    "онлайн-магазины",
    "сервисы впечатлений",
    "книжные магазины",
    "магазины для дома и уюта",
    "магазины косметики и ухода",
    "винтажные и блошиные рынки",
)


class Gift(BaseModel):
    """Одна идея подарка."""

    name: str = Field(
        min_length=2,
        max_length=120,
        description="Короткое название идеи без брендов и точных моделей.",
    )
    why: str = Field(
        min_length=10,
        max_length=400,
        description="1–2 предложения: почему идея подойдёт именно этому человеку.",
    )
    price_min: int = Field(
        ge=1,
        le=1_000_000,
        description="Нижняя граница примерной цены в рублях.",
    )
    price_max: int = Field(
        ge=1,
        le=1_000_000,
        description="Верхняя граница примерной цены в рублях.",
    )
    category: GiftCategory = Field(
        description="Где искать подарок — одно значение из списка.",
    )

    @field_validator("name", "why")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("category", mode="before")
    @classmethod
    def _normalize_category(cls, value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.strip().lower().split())
        return value

    @model_validator(mode="after")
    def _check_price_range(self) -> "Gift":
        if self.price_min > self.price_max:
            raise ValueError("price_min не может быть больше price_max")
        return self


class GiftResponse(BaseModel):
    """Ответ AI: ровно пять идей."""

    gifts: list[Gift] = Field(
        min_length=5,
        max_length=5,
        description="Ровно 5 разных идей подарка.",
    )

    @model_validator(mode="after")
    def _check_unique_names(self) -> "GiftResponse":
        names = [gift.name.casefold().strip() for gift in self.gifts]
        if len(set(names)) != len(names):
            raise ValueError("Идеи должны быть разными, названия не должны повторяться")
        return self

    def over_budget(self, budget_rub: int) -> list[Gift]:
        """Возвращает идеи, которые выходят за бюджет."""

        return [gift for gift in self.gifts if gift.price_max > budget_rub]

    def check_budget(self, budget_rub: int) -> None:
        """Бросает ValueError, если хотя бы одна идея дороже бюджета."""

        over = self.over_budget(budget_rub)
        if not over:
            return
        details = ", ".join(
            f"«{gift.name}» — до {gift.price_max} ₽" for gift in over
        )
        raise ValueError(
            f"Бюджет {budget_rub} ₽ превышен: {details}"
        )
