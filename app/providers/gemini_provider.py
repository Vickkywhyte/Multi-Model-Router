"""Google Gemini provider adapter using the google-genai SDK."""

from decimal import Decimal

from google import genai
from google.genai import types

from app.config import get_settings
from app.observability.logger import get_logger
from app.providers.base import BaseProvider, CompletionRequest, CompletionResult

logger = get_logger("app.providers.gemini")

_PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "gemini-3.5-flash-lite": (Decimal("0.30"), Decimal("2.50")),
    "gemini-3.5-flash":      (Decimal("1.50"), Decimal("9.00")),
    "gemini-2.5-pro":        (Decimal("1.25"), Decimal("10.00")),
}


class GeminiProvider(BaseProvider):
    """Adapter for Google Gemini models (free-tier compatible)."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        """Call Gemini and return a normalised CompletionResult.

        Args:
            request: Prompt, model name, and generation parameters.

        Returns:
            CompletionResult with text, token counts, and raw metadata.

        Raises:
            ValueError: If model_name is not supported by this provider.
        """
        if not self.supports(request.model_name):
            raise ValueError(
                f"GeminiProvider does not support model '{request.model_name}'. "
                f"Known models: {list(_PRICING)}"
            )

        logger.info("Calling Gemini", extra={"model": request.model_name})

        response = await self._client.aio.models.generate_content(
            model=request.model_name,
            contents=request.prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=request.max_tokens,
                temperature=request.temperature,
            ),
        )

        usage = getattr(response, "usage_metadata", None)
        tokens_in = getattr(usage, "prompt_token_count", 0) or 0
        tokens_out = getattr(usage, "candidates_token_count", 0) or 0

        logger.info(
            "Gemini response received",
            extra={
                "model": request.model_name,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
            },
        )

        return CompletionResult(
            text=response.text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model_name=request.model_name,
            raw={"usage_metadata": str(usage)} if usage else None,
        )

    def calculate_cost(
        self, model_name: str, tokens_in: int, tokens_out: int
    ) -> Decimal:
        """Return USD cost for the given token counts.

        Args:
            model_name: Gemini model identifier.
            tokens_in: Prompt token count.
            tokens_out: Completion token count.

        Returns:
            Total cost in USD as a Decimal.
        """
        if model_name not in _PRICING:
            raise ValueError(f"Unknown model for cost calculation: '{model_name}'")
        price_in, price_out = _PRICING[model_name]
        return (
            Decimal(tokens_in) * price_in / Decimal("1000000")
            + Decimal(tokens_out) * price_out / Decimal("1000000")
        )

    def supports(self, model_name: str) -> bool:
        """Return True if model_name is a known Gemini model.

        Args:
            model_name: The model identifier to check.
        """
        return model_name in _PRICING
