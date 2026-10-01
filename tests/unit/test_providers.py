"""Unit tests for the provider abstraction layer.

No real API calls are made — google.genai is fully mocked.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.base import CompletionRequest, CompletionResult
from app.providers.factory import get_provider
from app.providers.gemini_provider import GeminiProvider

# ---------------------------------------------------------------------------
# supports()
# ---------------------------------------------------------------------------

def test_supports_known_models() -> None:
    provider = GeminiProvider()
    assert provider.supports("gemini-3.5-flash-lite") is True
    assert provider.supports("gemini-3.5-flash") is True


def test_supports_unknown_model_returns_false() -> None:
    provider = GeminiProvider()
    assert provider.supports("gpt-4") is False
    assert provider.supports("") is False


# ---------------------------------------------------------------------------
# calculate_cost()
# ---------------------------------------------------------------------------

def test_calculate_cost_flash() -> None:
    provider = GeminiProvider()
    # 1000 input @ 1.50/1M + 500 output @ 9.00/1M
    # = 0.001500 + 0.004500 = 0.006000
    cost = provider.calculate_cost("gemini-3.5-flash", 1000, 500)
    assert cost == Decimal("0.006000")


def test_calculate_cost_flash_lite() -> None:
    provider = GeminiProvider()
    # 2000 input @ 0.30/1M + 1000 output @ 2.50/1M
    # = 0.000600 + 0.002500 = 0.003100
    cost = provider.calculate_cost("gemini-3.5-flash-lite", 2000, 1000)
    assert cost == Decimal("0.003100")



def test_calculate_cost_unknown_model_raises() -> None:
    provider = GeminiProvider()
    with pytest.raises(ValueError, match="Unknown model"):
        provider.calculate_cost("gpt-4o", 100, 100)


# ---------------------------------------------------------------------------
# factory
# ---------------------------------------------------------------------------

def test_get_provider_google_returns_gemini() -> None:
    provider = get_provider("google")
    assert isinstance(provider, GeminiProvider)


def test_get_provider_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("unknown")


# ---------------------------------------------------------------------------
# complete() — mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_complete_returns_result() -> None:
    mock_usage = MagicMock()
    mock_usage.prompt_token_count = 10
    mock_usage.candidates_token_count = 20

    mock_response = MagicMock()
    mock_response.text = "Hello, world!"
    mock_response.usage_metadata = mock_usage

    mock_aio_models = MagicMock()
    mock_aio_models.generate_content = AsyncMock(return_value=mock_response)

    mock_aio = MagicMock()
    mock_aio.models = mock_aio_models

    mock_client_instance = MagicMock()
    mock_client_instance.aio = mock_aio

    with patch("app.providers.gemini_provider.genai.Client", return_value=mock_client_instance):
        provider = GeminiProvider()
        result = await provider.complete(
            CompletionRequest(prompt="Hi", model_name="gemini-3.5-flash")
        )

    assert isinstance(result, CompletionResult)
    assert result.text == "Hello, world!"
    assert result.tokens_in == 10
    assert result.tokens_out == 20
    assert result.model_name == "gemini-3.5-flash"


@pytest.mark.asyncio
async def test_complete_unsupported_model_raises() -> None:
    provider = GeminiProvider()
    with pytest.raises(ValueError, match="does not support"):
        await provider.complete(
            CompletionRequest(prompt="Hi", model_name="gpt-4o")
        )
