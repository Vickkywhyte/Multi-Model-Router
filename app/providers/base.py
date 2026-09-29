"""Abstract provider interface for LLM completions.

All LLM providers implement BaseProvider so business logic never depends on
a specific SDK.  Adding a new provider (e.g. OpenAI) requires only a new
file that subclasses BaseProvider — no changes to routing or classification
code are needed.

Contract:
- complete()        — async, takes CompletionRequest, returns CompletionResult
- calculate_cost()  — sync, returns Decimal cost in USD
- supports()        — sync, returns True if this provider handles model_name
"""

from abc import ABC, abstractmethod
from decimal import Decimal

from pydantic import BaseModel


class CompletionRequest(BaseModel):
    """Input DTO for a single LLM completion call."""

    prompt: str
    model_name: str
    max_tokens: int = 1024
    temperature: float = 0.0


class CompletionResult(BaseModel):
    """Output DTO returned by every provider."""

    text: str
    tokens_in: int
    tokens_out: int
    model_name: str
    raw: dict[str, object] | None = None


class BaseProvider(ABC):
    """Uniform interface every LLM provider adapter must implement."""

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResult:
        """Send a prompt and return the completion.

        Args:
            request: The completion parameters.

        Returns:
            A CompletionResult with text, token counts, and optional raw metadata.
        """

    @abstractmethod
    def calculate_cost(
        self, model_name: str, tokens_in: int, tokens_out: int
    ) -> Decimal:
        """Return the USD cost for a given token usage.

        Args:
            model_name: The model identifier.
            tokens_in: Number of input/prompt tokens.
            tokens_out: Number of output/completion tokens.

        Returns:
            Cost in USD as a Decimal.
        """

    @abstractmethod
    def supports(self, model_name: str) -> bool:
        ...
