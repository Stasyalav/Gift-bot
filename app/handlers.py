"""Обработчики сообщений: диалог, подборка и кнопки результата."""

from __future__ import annotations

import json
import logging

from vkbottle.bot import Bot, Message

from app.ai import AIError, GiftAI
from app.budget import format_rub
from app.config import Config
from app.dialogue import plan_brief
from app.formatting import format_gifts, split_for_vk
from app.images import GreetingImages
from app.keyboards import (
    help_keyboard,
    results_keyboard,
    retry_keyboard,
    start_keyboard,
)
from app.states import AWAITING_ANSWER, AWAITING_BRIEF, IDLE, RESULTS, UserState, get_state

logger = logging.getLogger(__name__)

GREETING_TEXT = (
    "Добрый день 🌸\n"
    "Я помогу подобрать подарок — бережно, с вниманием к деталям и вашему бюджету.\n\n"
    "Чтобы подборка получилась точной, расскажите хотя бы немного:\n"
    "• пол и возраст\n"
    "• кто это — мама, друг, коллега…\n"
    "• повод\n"
    "• увлечения\n"
    "• что любит и что не любит\n"
    "• бюджет — до какой суммы\n"
    "• всё остальное, что важно\n\n"
    "Можно писать свободно и не по порядку. Обязателен только бюджет 🙂"
)

HELP_TEXT = (
    "Это просто:\n"
    "1. Вы рассказываете, кому и на какой повод ищете подарок.\n"
    "2. Я предлагаю 5 идей с примерными ценами и объяснением, почему они подойдут.\n"
    "3. Можно попросить другую подборку или изменить критерии.\n\n"
    "Обязательное условие — назвать бюджет, хотя бы примерно. Например:\n"
    "«Маме на день рождения, любит уют и книги, до 5 000 ₽»."
)

BUDGET_QUESTION = (
    "Понял вас 🌸\n"
    "Чтобы подборка была по карману, назовите бюджет — до какой суммы искать.\n"
    "Например: «до 5 000 ₽»."
)

ASK_BRIEF_TEXT = (
    "Бюджет записал ✅\n"
    "Теперь расскажите, кому и на какой повод ищете подарок: кто это, "
    "сколько лет, чем увлекается, что любит."
)

EDIT_TEXT = (
    "Хорошо, расскажите заново — что важно учесть?\n"
    "Кому и на какой повод, увлечения, что любит и что не любит. "
    "Бюджет можно назвать новый или оставить прежний."
)

GENERATING_TEXT = "Секунду, подбираю идеи… 🌸"

AI_UNAVAILABLE_TEXT = (
    "Подбор идей пока недоступен: не настроен доступ к GigaChat.\n"
    "Напишите администратору сообщества — он проверит ключ в настройках."
)

AI_ERROR_PREFIX = "Не получилось собрать подборку 😔"

UNEXPECTED_ERROR_TEXT = (
    "Что-то пошло не так при обращении к GigaChat. "
    "Попробуйте ещё раз через минуту."
)

THANKS_WORDS = {
    "спасибо",
    "спасибо!",
    "благодарю",
    "спс",
    "класс",
    "супер",
    "отлично",
    "здорово",
}
GREETING_WORDS = {"привет", "здравствуйте", "добрый день", "добрый вечер", "хай"}
START_WORDS = {"/start", "начать", "start", "меню"}
HELP_WORDS = {"как это работает", "помощь", "help"}


def _payload_command(message: Message) -> str | None:
    payload = message.payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None
    if isinstance(payload, dict):
        command = payload.get("cmd")
        return str(command) if command else None
    return None


def _clear_dialogue(state: UserState) -> None:
    """Сбрасывает описание и бюджет, но помнит последнюю картинку."""

    state.stage = AWAITING_BRIEF
    state.brief = None
    state.budget_rub = None
    state.last_gifts = []


async def _send_greeting(
    message: Message, state: UserState, images: GreetingImages
) -> None:
    _clear_dialogue(state)
    path = images.pick(state.last_image)
    attachment = await images.upload(path, message.peer_id)
    if path is not None:
        state.last_image = path.name

    await message.answer(
        GREETING_TEXT,
        attachment=attachment,
        keyboard=start_keyboard(),
    )


async def _generate(
    message: Message,
    state: UserState,
    ai: GiftAI | None,
    budget_rub: int,
    *,
    avoid_names: list[str] | None = None,
) -> None:
    if ai is None:
        state.stage = AWAITING_BRIEF
        await message.answer(AI_UNAVAILABLE_TEXT, keyboard=help_keyboard())
        return

    if not state.brief:
        state.stage = AWAITING_BRIEF
        await message.answer(ASK_BRIEF_TEXT, keyboard=help_keyboard())
        return

    state.stage = AWAITING_ANSWER
    await message.answer(GENERATING_TEXT)

    try:
        gifts = await ai.suggest(state.brief, budget_rub, avoid_names=avoid_names)
    except AIError as exc:
        logger.warning("AIError для %s: %s", message.from_id, exc)
        state.stage = RESULTS
        await message.answer(
            f"{AI_ERROR_PREFIX}\n\n{exc}",
            keyboard=retry_keyboard(),
        )
        return
    except Exception:  # noqa: BLE001 — пользователь не должен видеть трейсбек
        logger.exception("Неожиданная ошибка AI для %s", message.from_id)
        state.stage = RESULTS
        await message.answer(UNEXPECTED_ERROR_TEXT, keyboard=retry_keyboard())
        return

    state.last_gifts = [gift.name for gift in gifts]
    state.stage = RESULTS

    intro = None
    if avoid_names:
        intro = f"Вот ещё 5 идей — уже другие, до {format_rub(budget_rub)}:"
    text = format_gifts(gifts, budget_rub, intro=intro)

    parts = split_for_vk(text)
    for index, part in enumerate(parts):
        is_last = index == len(parts) - 1
        await message.answer(
            part,
            keyboard=results_keyboard() if is_last else None,
        )


async def _handle_brief(
    message: Message,
    state: UserState,
    ai: GiftAI | None,
    config: Config,
    text: str,
) -> None:
    plan = plan_brief(state, text, max_budget_rub=config.max_budget_rub)

    if plan.capped and plan.budget_rub is not None:
        await message.answer(
            f"Максимум в этом боте — {format_rub(plan.budget_rub)}. "
            "Подберу идеи в этих пределах."
        )

    if plan.action == "need_brief":
        await message.answer(ASK_BRIEF_TEXT, keyboard=help_keyboard())
        return

    if plan.action == "need_budget":
        await message.answer(BUDGET_QUESTION, keyboard=help_keyboard())
        return

    if plan.budget_rub is None:
        await message.answer(BUDGET_QUESTION, keyboard=help_keyboard())
        return

    if plan.reused_budget:
        await message.answer(
            f"Бюджет оставляю прежним — до {format_rub(plan.budget_rub)}."
        )

    await _generate(message, state, ai, plan.budget_rub)


def register_handlers(
    bot: Bot,
    config: Config,
    images: GreetingImages,
    ai: GiftAI | None,
) -> None:
    @bot.on.message()
    async def handle_message(message: Message) -> None:
        text = (message.text or "").strip()
        lowered = text.lower()
        command = _payload_command(message)
        state = get_state(message.from_id)

        logger.info(
            "Сообщение от %s: %r (stage=%s, cmd=%s)",
            message.from_id,
            text,
            state.stage,
            command,
        )

        if command == "help" or lowered in HELP_WORDS:
            await message.answer(HELP_TEXT, keyboard=help_keyboard())
            return

        # Пока идёт запрос к GigaChat, не начинаем второй диалог.
        if state.stage == AWAITING_ANSWER:
            await message.answer("Ещё секунду — собираю идеи… 🌸")
            return

        if command in {"start", "restart"} or lowered in START_WORDS:
            await _send_greeting(message, state, images)
            return

        if command == "edit":
            state.stage = AWAITING_BRIEF
            state.brief = None
            state.last_gifts = []
            await message.answer(EDIT_TEXT, keyboard=help_keyboard())
            return

        if command in {"more", "retry"}:
            if state.brief and state.budget_rub is not None:
                await _generate(
                    message,
                    state,
                    ai,
                    state.budget_rub,
                    avoid_names=state.last_gifts or None,
                )
            else:
                await _send_greeting(message, state, images)
            return

        if state.stage == IDLE:
            await _send_greeting(message, state, images)
            return

        if not text:
            await message.answer(
                "Напишите, пожалуйста, текстом — так я лучше пойму, "
                "что нужно 🌸",
                keyboard=help_keyboard(),
            )
            return

        if lowered in THANKS_WORDS:
            keyboard = results_keyboard() if state.stage == RESULTS else help_keyboard()
            await message.answer(
                "Рада, что помогла 🌸 Если захочется другую подборку — "
                "нажмите кнопку ниже.",
                keyboard=keyboard,
            )
            return

        if lowered in GREETING_WORDS:
            await message.answer(
                "Здравствуйте! Расскажите, кому и на какой повод ищете "
                "подарок, и назовите бюджет — я предложу 5 идей 🌸",
                keyboard=help_keyboard(),
            )
            return

        if state.stage == RESULTS:
            # Свободный текст после подборки считаем новым запросом:
            # бюджет нужно назвать заново.
            state.brief = None
            state.budget_rub = None
            state.last_gifts = []

        if state.stage in {AWAITING_BRIEF, RESULTS}:
            await _handle_brief(message, state, ai, config, text)
            return

        await _send_greeting(message, state, images)
