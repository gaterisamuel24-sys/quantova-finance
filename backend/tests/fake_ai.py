"""A stand-in for the AI provider, so tests never call a paid API or need a key."""

from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel

from app.services.ai.model import AIProviderError, ModelReply


@dataclass
class FakeInsightModel:
    """Returns whatever `respond` builds, and records every request it receives.

    `respond` gets the output type and the input text and returns an instance of that
    type. Set `fail` to make every call raise AIProviderError instead.
    """

    respond: Callable[[type[BaseModel], str], BaseModel] | None = None
    fail: bool = False
    calls: list[dict[str, object]] = field(default_factory=list)

    async def generate[T: BaseModel](
        self, *, instructions: str, input_text: str, output_type: type[T]
    ) -> ModelReply[T]:
        self.calls.append({"instructions": instructions, "input_text": input_text})
        if self.fail:
            raise AIProviderError("The AI service is unavailable. Try again later.")
        if self.respond is None:
            raise AssertionError("FakeInsightModel.respond was not set")
        output = self.respond(output_type, input_text)
        if not isinstance(output, output_type):
            raise AssertionError(f"respond returned {type(output).__name__}, not {output_type}")
        return ModelReply(output=output, model="fake-model", input_tokens=100, output_tokens=50)
