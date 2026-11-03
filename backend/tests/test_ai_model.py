"""The OpenAI adapter: what it sends, what it returns, and how failures are reported.

A fake client stands in for OpenAI, so these tests make no network calls.
"""

from types import SimpleNamespace
from typing import Any, cast

import openai
import pytest
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.services.ai.model import AIProviderError, AIUnavailableError
from app.services.ai.openai_model import OpenAIInsightModel, build_insight_model
from tests.conftest import SettingsFactory

pytestmark = pytest.mark.anyio


class Answer(BaseModel):
    headline: str


class FakeResponses:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.kwargs: dict[str, Any] = {}

    async def parse(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        return self.result


def fake_client(responses: FakeResponses) -> AsyncOpenAI:
    return cast(AsyncOpenAI, SimpleNamespace(responses=responses))


def parsed_response(output: BaseModel | None, *, usage: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        output_parsed=output,
        model="gpt-test-2026",
        status="completed" if output else "incomplete",
        usage=SimpleNamespace(input_tokens=1200, output_tokens=340) if usage else None,
    )


def test_without_a_key_ai_is_unavailable(settings_factory: SettingsFactory) -> None:
    # Explicit None: a developer's own OPENAI_API_KEY environment variable must not leak in.
    settings = settings_factory(openai_api_key=None)
    assert settings.ai_enabled is False
    with pytest.raises(AIUnavailableError):
        build_insight_model(settings)


def test_a_blank_key_counts_as_no_key(settings_factory: SettingsFactory) -> None:
    assert settings_factory(openai_api_key="   ").ai_enabled is False


def test_the_key_is_never_shown(settings_factory: SettingsFactory) -> None:
    settings = settings_factory(openai_api_key="sk-test-not-a-real-key")
    for view in (repr(settings), str(settings), str(settings.model_dump())):
        assert "sk-test-not-a-real-key" not in view


async def test_sends_a_private_structured_request(settings_factory: SettingsFactory) -> None:
    settings = settings_factory(openai_api_key="sk-test", openai_model="gpt-test")
    responses = FakeResponses(result=parsed_response(Answer(headline="Revenue grew")))
    model = OpenAIInsightModel(settings, client=fake_client(responses))

    reply = await model.generate(instructions="Explain.", input_text="{}", output_type=Answer)

    assert reply.output == Answer(headline="Revenue grew")
    assert (reply.model, reply.input_tokens, reply.output_tokens) == ("gpt-test-2026", 1200, 340)
    assert responses.kwargs["model"] == "gpt-test"
    assert responses.kwargs["text_format"] is Answer
    assert responses.kwargs["store"] is False  # OpenAI must not keep the response
    assert responses.kwargs["max_output_tokens"] == settings.ai_max_output_tokens


async def test_missing_usage_counts_as_zero(settings_factory: SettingsFactory) -> None:
    responses = FakeResponses(result=parsed_response(Answer(headline="x"), usage=False))
    model = OpenAIInsightModel(
        settings_factory(openai_api_key="sk-test"), client=fake_client(responses)
    )

    reply = await model.generate(instructions="", input_text="", output_type=Answer)

    assert (reply.input_tokens, reply.output_tokens) == (0, 0)


async def test_no_structured_output_is_an_error(settings_factory: SettingsFactory) -> None:
    responses = FakeResponses(result=parsed_response(None))
    model = OpenAIInsightModel(
        settings_factory(openai_api_key="sk-test"), client=fake_client(responses)
    )

    with pytest.raises(AIProviderError, match="usable answer"):
        await model.generate(instructions="", input_text="", output_type=Answer)


def provider_error[E: Exception](error_type: type[E]) -> E:
    """An OpenAI exception of the given type, without building HTTP request objects.

    Only the type matters to the adapter. The message deliberately contains a fake key,
    to prove that provider details never reach the user-facing message.
    """
    error = error_type.__new__(error_type)
    Exception.__init__(error, "Incorrect API key provided: sk-test")
    return error


@pytest.mark.parametrize(
    ("error_type", "message"),
    [
        (openai.APITimeoutError, "took too long"),
        (openai.RateLimitError, "busy"),
        (openai.AuthenticationError, "unavailable"),
        (openai.APIConnectionError, "unavailable"),
    ],
)
async def test_provider_failures_become_neutral_messages(
    settings_factory: SettingsFactory, error_type: type[Exception], message: str
) -> None:
    model = OpenAIInsightModel(
        settings_factory(openai_api_key="sk-test"),
        client=fake_client(FakeResponses(error=provider_error(error_type))),
    )

    with pytest.raises(AIProviderError, match=message) as exc_info:
        await model.generate(instructions="", input_text="", output_type=Answer)

    # Provider details (which can include parts of the key) never reach the user message.
    assert "sk-test" not in str(exc_info.value)
