"""The provider-neutral interface for asking an AI model for a structured answer.

The rest of the application depends on `InsightModel`, never on a vendor SDK, so:
- tests use a fake model and never call a paid API or need a key;
- the provider can be changed later by adding one adapter, without touching callers.
"""

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel


class AIUnavailableError(Exception):
    """AI features are switched off (no API key configured)."""


class AIProviderError(Exception):
    """The provider could not produce a usable answer: timeout, outage, refusal, bad output.

    The message is safe to show to users. Provider details are logged, never returned.
    """


@dataclass(frozen=True)
class ModelReply[T: BaseModel]:
    """A validated structured answer, with what it cost, for storage and auditing."""

    output: T
    model: str
    input_tokens: int
    output_tokens: int


class InsightModel(Protocol):
    """Anything that can turn instructions plus input data into a validated `output_type`."""

    async def generate[T: BaseModel](
        self, *, instructions: str, input_text: str, output_type: type[T]
    ) -> ModelReply[T]: ...
