import logging

import anthropic

from .catalog import Catalog

log = logging.getLogger(__name__)

# Модели, у которых есть серверный фолбэк при отказе (refusal)
FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}

SORRY = "Не получилось ответить 🙈 Попробуйте спросить иначе или позвоните нам: {phone}"

SYSTEM_PROMPT = """Ты — консультант «{name}» в Telegram-боте. Отвечаешь гостям на русском: коротко (1–3 предложения), тепло и по делу.

Правила:
- Опирайся только на данные о кофейне ниже. Не придумывай позиции, цены, акции и факты.
- Если ответа в данных нет — честно скажи и предложи уточнить у бариста по телефону {phone}.
- Сам заказы не оформляешь: чтобы заказать, гость нажимает кнопку «☕ Меню».
- Можешь советовать напитки по вкусу гостя, но только из меню.
- Пиши обычным текстом без Markdown, можно 1–2 эмодзи.
- На вопросы не про кофейню отвечай вежливо и возвращай разговор к кофейне.

<данные_кофейни>
{data}
</данные_кофейни>"""


class Consultant:
    """ИИ-консультант: отвечает на свободные вопросы по меню и информации о кофейне."""

    def __init__(self, api_key: str | None, model: str, catalog: Catalog):
        self._client = anthropic.AsyncAnthropic(api_key=api_key) if api_key else None
        self._model = model
        self._phone = catalog.shop["phone"]
        self._system = SYSTEM_PROMPT.format(name=catalog.shop["name"], phone=self._phone, data=catalog.as_text())

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def answer(self, question: str) -> str:
        params = dict(
            model=self._model,
            max_tokens=4000,
            system=self._system,
            messages=[{"role": "user", "content": question}],
            output_config={"effort": "low"},
        )
        try:
            if self._model in FALLBACK_MODELS:
                response = await self._client.beta.messages.create(
                    **params, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
                )
            else:
                response = await self._client.messages.create(**params)
        except anthropic.RateLimitError:
            log.warning("Claude: rate limit")
            return "Сейчас много вопросов, попробуйте через минуту 🙏"
        except anthropic.APIStatusError as e:
            log.error("Claude API error %s: %s", e.status_code, e.message)
            return SORRY.format(phone=self._phone)
        except anthropic.APIConnectionError:
            log.exception("Claude: нет соединения")
            return SORRY.format(phone=self._phone)

        if response.stop_reason == "refusal":
            return SORRY.format(phone=self._phone)
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        return text or SORRY.format(phone=self._phone)
