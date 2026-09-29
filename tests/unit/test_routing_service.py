"""Unit tests for app.services.routing_service — no real API or DB calls."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.providers.base import CompletionResult
from app.schemas.route import RouteRequest, RouteResponse
from app.services.routing_service import route_prompt


def _make_provider(
    text: str = "hello",
    tokens_in: int = 10,
    tokens_out: int = 20,
    model_name: str = "gemini-3.5-flash-lite",
    cost: Decimal = Decimal("0.000042"),
) -> MagicMock:
    provider = MagicMock()
    provider.complete = AsyncMock(
        return_value=CompletionResult(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model_name=model_name,
        )
    )
    provider.calculate_cost = MagicMock(return_value=cost)
    return provider


def _make_session(model_id: uuid.UUID | None = None) -> AsyncMock:
    session = AsyncMock()
    if model_id is not None:
        model_row = MagicMock()
        model_row.id = model_id
        scalar = MagicMock()
        scalar.scalar_one_or_none = MagicMock(return_value=model_row)
        session.execute = AsyncMock(return_value=scalar)
    else:
        scalar = MagicMock()
        scalar.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=scalar)
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_happy_path_returns_route_response() -> None:
    provider = _make_provider()
    session = _make_session(model_id=uuid.uuid4())
    req = RouteRequest(prompt="What is Python?")

    resp = await route_prompt(req, session, provider)

    assert isinstance(resp, RouteResponse)
    assert resp.text == "hello"
    assert resp.tokens_in == 10
    assert resp.tokens_out == 20
    assert resp.cost_usd == Decimal("0.000042")
    assert resp.latency_ms >= 0


@pytest.mark.asyncio
async def test_simple_prompt_routes_to_flash_lite() -> None:
    """A short factual question should map to gemini-3.5-flash-lite."""
    provider = _make_provider(model_name="gemini-3.5-flash-lite")
    session = _make_session(model_id=uuid.uuid4())
    req = RouteRequest(prompt="What is Python?")

    await route_prompt(req, session, provider)

    call_kwargs = provider.complete.call_args[0][0]
    assert call_kwargs.model_name == "gemini-3.5-flash-lite"


@pytest.mark.asyncio
async def test_complex_prompt_routes_to_pro() -> None:
    """A long, multi-step prompt with code fences should map to gemini-2.5-pro."""
    complex_prompt = (
        "Step by step, design and architect a distributed microservices system. "
        "Compare the tradeoffs, analyze the failure modes, and evaluate each component.\n"
        "```python\nprint('hello')\n```\n"
        "Explain why each design decision was made, critique the approach, "
        "and refactor the code to be more efficient. "
        "After that, prove the correctness of the algorithm with a formal proof. "
        "Also, provide an in depth analysis of the results."
    )
    provider = _make_provider(model_name="gemini-2.5-pro")
    session = _make_session(model_id=uuid.uuid4())
    req = RouteRequest(prompt=complex_prompt)

    await route_prompt(req, session, provider)

    call_kwargs = provider.complete.call_args[0][0]
    assert call_kwargs.model_name == "gemini-2.5-pro"


@pytest.mark.asyncio
async def test_request_id_is_valid_uuid4() -> None:
    provider = _make_provider()
    session = _make_session(model_id=uuid.uuid4())
    req = RouteRequest(prompt="What is Python?")

    resp = await route_prompt(req, session, provider)

    parsed = uuid.UUID(resp.request_id, version=4)
    assert str(parsed) == resp.request_id


@pytest.mark.asyncio
async def test_cost_usd_is_decimal_and_matches_provider() -> None:
    expected_cost = Decimal("0.001234")
    provider = _make_provider(cost=expected_cost)
    session = _make_session(model_id=uuid.uuid4())
    req = RouteRequest(prompt="What is Python?")

    resp = await route_prompt(req, session, provider)

    assert isinstance(resp.cost_usd, Decimal)
    assert resp.cost_usd == expected_cost


@pytest.mark.asyncio
async def test_provider_exception_persists_error_row_and_reraises() -> None:
    provider = MagicMock()
    provider.complete = AsyncMock(side_effect=RuntimeError("API down"))
    session = _make_session(model_id=uuid.uuid4())
    req = RouteRequest(prompt="What is Python?")

    with pytest.raises(RuntimeError, match="API down"):
        await route_prompt(req, session, provider)

    session.add.assert_called_once()
    added_row = session.add.call_args[0][0]
    assert added_row.status == "error"
    assert "API down" in added_row.error_message


@pytest.mark.asyncio
async def test_missing_model_row_does_not_crash() -> None:
    """If the Model row isn't in the DB, response is still returned (no crash)."""
    provider = _make_provider()
    session = _make_session(model_id=None)  # simulate missing model row
    req = RouteRequest(prompt="What is Python?")

    resp = await route_prompt(req, session, provider)

    assert isinstance(resp, RouteResponse)
    # DB insert was skipped — add should not have been called
    session.add.assert_not_called()
