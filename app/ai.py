"""Работа с GigaChat: генерация подборки, проверки и повтор.

Модель может ошибиться: вернуть не 5 идей, превысить бюджет или нарушить
схему. Поэтому её ответ всегда проверяется кодом. При ошибке делаем одну
повторную попытку — уже с указанием, что именно нужно исправить.
"""

from __future__ import annotations

import json
import logging
import re

import httpx
from gigachat import GigaChat
from gigachat.exceptions import (
    AuthenticationError,
    BadRequestError,
    ForbiddenError,
    GigaChatException,
    LengthFinishReasonError,
    RateLimitError,
    ResponseError,
    UnprocessableEntityError,
)
from pydantic import ValidationError

from app.config import Config, require_gigachat_credentials
from app.prompts import PLAIN_JSON_INSTRUCTION, SYSTEM_PROMPT, build_user_prompt
from app.schemas import Gift, GiftResponse

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2
MAX_TOKENS = 2200
TEMPERATURE = 0.7


class AIError(RuntimeError):
    """Ошибка AI с понятным пользователю текстом."""


def _friendly_error(exc: Exception) -> str:
    """Переводит техническую ошибку в короткую фразу для пользователя."""

    if isinstance(exc, AuthenticationError):
        return (
            "GigaChat не принял ключ доступа. Проверьте GIGACHAT_CREDENTIALS "
            "в файле .env."
        )
    if isinstance(exc, ForbiddenError):
        return (
            "У ключа GigaChat нет доступа к выбранной модели или тарифу. "
            "Проверьте GIGACHAT_SCOPE и GIGACHAT_MODEL."
        )
    if isinstance(exc, RateLimitError):
        return "GigaChat временно ограничил частоту запросов. Попробуйте через минуту."
    if isinstance(exc, httpx.TimeoutException):
        return "GigaChat не ответил вовремя. Попробуйте ещё раз."
    if isinstance(exc, httpx.ConnectError):
        return (
            "Не удалось соединиться с GigaChat. Проверьте интернет и сертификат "
            "Минцифры в папке certs."
        )
    if isinstance(exc, ResponseError):
        return f"GigaChat вернул ошибку {exc.status_code}. Попробуйте ещё раз."
    if isinstance(exc, GigaChatException):
        return "GigaChat не смог подготовить подборку. Попробуйте ещё раз."
    if isinstance(exc, (ValidationError, ValueError)):
        return "GigaChat вернул ответ не по правилам. Попробуйте ещё раз."
    return "Не получилось получить подборку от GigaChat. Попробуйте ещё раз."


def _strip_code_fence(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _response_text(completion: object) -> str:
    """Достаёт текст ответа из ChatCompletionResponse."""

    messages = getattr(completion, "messages", None) or []
    chunks: list[str] = []
    for message in messages:
        if getattr(message, "role", None) != "assistant":
            continue
        for part in getattr(message, "content", None) or []:
            text = getattr(part, "text", None)
            if text:
                chunks.append(text)
    return "".join(chunks).strip()


class GiftAI:
    """Клиент GigaChat для подбора подарков."""

    def __init__(self, config: Config) -> None:
        credentials = require_gigachat_credentials(config)
        kwargs: dict[str, object] = {
            "credentials": credentials,
            "scope": config.gigachat_scope,
            "model": config.gigachat_model,
            "timeout": config.gigachat_timeout_seconds,
            "max_retries": config.gigachat_max_retries,
        }

        ca_bundle = config.gigachat_ca_bundle_file
        if ca_bundle.exists():
            kwargs["ca_bundle_file"] = str(ca_bundle)
        else:
            logger.warning(
                "Сертификат Минцифры не найден: %s. Если GigaChat не отвечает "
                "из-за TLS, скачайте PEM-версию: "
                "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt",
                ca_bundle,
            )

        self._client = GigaChat(**kwargs)  # type: ignore[arg-type]
        self._model = config.gigachat_model

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request_structured(self, payload: dict[str, object]) -> GiftResponse:
        completion, parsed = await self._client.achat.parse(
            payload,
            response_format=GiftResponse,
            strict=True,
        )
        self._log_usage(completion)
        return parsed

    async def _request_plain_json(self, payload: dict[str, object]) -> GiftResponse:
        """Запасной путь: просим JSON обычным текстом и разбираем сами."""

        plain_payload = dict(payload)
        messages = list(payload.get("messages", []))  # type: ignore[arg-type]
        if messages:
            first = dict(messages[0])
            first["content"] = str(first.get("content", "")) + PLAIN_JSON_INSTRUCTION
            messages[0] = first
        plain_payload["messages"] = messages

        completion = await self._client.achat.create(plain_payload)
        self._log_usage(completion)
        raw = _response_text(completion)
        if not raw:
            raise ValueError("GigaChat вернул пустой ответ")

        data = json.loads(_strip_code_fence(raw))
        return GiftResponse.model_validate(data)

    @staticmethod
    def _log_usage(completion: object) -> None:
        usage = getattr(completion, "usage", None)
        if usage is not None:
            logger.info(
                "GigaChat: токенов %s",
                getattr(usage, "total_tokens", "?"),
            )

    async def _request(
        self, payload: dict[str, object], *, structured: bool
    ) -> GiftResponse:
        if structured:
            return await self._request_structured(payload)
        return await self._request_plain_json(payload)

    async def suggest(
        self,
        brief: str,
        budget_rub: int,
        *,
        avoid_names: list[str] | None = None,
    ) -> list[Gift]:
        """Возвращает ровно 5 идей, проверенных по схеме и бюджету."""

        problems: list[str] = []
        last_error: Exception | None = None
        structured = True

        for attempt in range(1, MAX_ATTEMPTS + 1):
            payload: dict[str, object] = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_user_prompt(
                            brief,
                            budget_rub,
                            problems=problems or None,
                            avoid_names=avoid_names,
                        ),
                    },
                ],
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
            }

            logger.info(
                "GigaChat: попытка %s/%s, бюджет %s ₽, описание %s символов, "
                "формат %s",
                attempt,
                MAX_ATTEMPTS,
                budget_rub,
                len(brief),
                "structured" if structured else "plain-json",
            )

            try:
                parsed = await self._request(payload, structured=structured)
            except LengthFinishReasonError as exc:
                last_error = exc
                structured = False
                problems = [
                    "Ответ получился слишком длинным и обрезался. "
                    "Сделай описания короче."
                ]
                logger.warning("GigaChat обрезал ответ по длине")
                continue
            except (BadRequestError, UnprocessableEntityError) as exc:
                last_error = exc
                structured = False
                problems = []
                logger.warning(
                    "GigaChat отклонил структурированный ответ (%s), "
                    "пробую обычный JSON",
                    exc,
                )
                continue
            except (ValidationError, ValueError) as exc:
                last_error = exc
                structured = False
                problems = [
                    "Ответ не соответствует требуемой структуре. Проверь, что "
                    "в gifts ровно 5 идей, у каждой есть name, why, price_min, "
                    "price_max и допустимая category."
                ]
                logger.warning("GigaChat вернул ответ не по схеме: %s", exc)
                continue
            except Exception as exc:  # noqa: BLE001 — наружу отдаём понятный текст
                last_error = exc
                logger.exception("Ошибка при запросе к GigaChat")
                raise AIError(_friendly_error(exc)) from exc

            over_budget = parsed.over_budget(budget_rub)
            if over_budget:
                structured = False
                problems = [
                    f"«{gift.name}» стоит до {gift.price_max} ₽, "
                    f"а бюджет — {budget_rub} ₽. Уложись в бюджет."
                    for gift in over_budget
                ]
                logger.warning(
                    "GigaChat превысил бюджет %s ₽: %s",
                    budget_rub,
                    ", ".join(gift.name for gift in over_budget),
                )
                continue

            return parsed.gifts

        logger.error("Не удалось получить корректную подборку: %s", last_error)
        if isinstance(last_error, LengthFinishReasonError):
            raise AIError(
                "GigaChat не уложился в длину ответа. Попробуйте ещё раз."
            )
        raise AIError(
            "GigaChat дважды вернул ответ, который не прошёл проверку. "
            "Попробуйте ещё раз."
        )
