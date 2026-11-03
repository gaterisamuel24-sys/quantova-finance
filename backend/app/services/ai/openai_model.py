"""`InsightModel` backed by the OpenAI Responses API with Structured Outputs.

Structured Outputs constrains the model to answer with JSON matching our Pydantic
schema, and the SDK parses it straight back into that model, so free-form text is
never parsed by hand.

Privacy settings on every request:
- `store=False`: OpenAI does not keep the response for later retrieval.
- No user names, emails or organization identifiers are sent; callers pass only
  the aggregated figures they choose (see the insights service).
"""

import logging

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import Settings
from app.services.ai.model import AIProviderError, AIUnavailableError, ModelReply

logger = logging.getLogger(__name__)

MAX_RETRIES = 2  # the SDK retries connection errors, 429 and 5xx with backoff


class OpenAIInsightModel:
    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None) -> None:
        if settings.openai_api_key is None:
            raise AIUnavailableError("AI insights are not configured.")
        self._model = settings.openai_model
        self._max_output_tokens = settings.ai_max_output_tokens
        self._client = client or AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.ai_request_timeout_seconds,
            max_retries=MAX_RETRIES,
        )

    async def generate[T: BaseModel](
        self, *, instructions: str, input_text: str, output_type: type[T]
    ) -> ModelReply[T]:
        try:
            response = await self._client.responses.parse(
                model=self._model,
                instructions=instructions,
                input=input_text,
                text_format=output_type,
                max_output_tokens=self._max_output_tokens,
                store=False,
            )
        except openai.APITimeoutError as exc:
            logger.warning("OpenAI request timed out")
            raise AIProviderError("The AI service took too long to respond. Try again.") from exc
        except openai.RateLimitError as exc:
            logger.warning("OpenAI rate limit or quota reached")
            raise AIProviderError("The AI service is busy right now. Try again later.") from exc
        except openai.OpenAIError as exc:
            # Covers authentication, bad requests, outages and connection errors. The
            # details go to the server log only; users get a neutral message.
            logger.error("OpenAI request failed: %s", type(exc).__name__)
            raise AIProviderError("The AI service is unavailable. Try again later.") from exc

        parsed = response.output_parsed
        if parsed is None:
            # A refusal, or output cut off by the token limit, yields no parsed object.
            logger.warning("OpenAI returned no structured output (status=%s)", response.status)
            raise AIProviderError("The AI service did not return a usable answer. Try again.")

        usage = response.usage
        return ModelReply(
            output=parsed,
            model=response.model,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
        )


def build_insight_model(settings: Settings) -> OpenAIInsightModel:
    """The configured model. Raises AIUnavailableError when no API key is set."""
    return OpenAIInsightModel(settings)
