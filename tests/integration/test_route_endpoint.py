"""Integration tests for POST /v1/route endpoint."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.route import get_provider_dep
from app.api.v1.route import router as route_router
from app.dependencies import get_db
from app.models.model import Model
from app.providers.base import CompletionResult

# Minimal test app — no tracing middleware so X-Request-ID header is ours alone.
_test_app = FastAPI()
_test_app.include_router(route_router, prefix="/v1")


def _make_mock_session(model_name: str = "gemini-3.5-flash-lite") -> MagicMock:
    """Return a mock AsyncSession that returns a fake Model row on execute."""
    model_row = Model(
        id=uuid.uuid4(),
        name=model_name,
        provider="google",
        input_price_per_million=0.0,
        output_price_per_million=0.0,
        context_window=1_000_000,
    )

    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = model_row

    session = MagicMock()
    session.execute = AsyncMock(return_value=scalar_result)
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


def _make_mock_provider(
    text: str = "Hello!",
    tokens_in: int = 10,
    tokens_out: int = 5,
    model_name: str = "gemini-3.5-flash-lite",
    raise_exc: Exception | None = None,
) -> MagicMock:
    """Return a mock BaseProvider."""
    provider = MagicMock()

    if raise_exc is not None:
        provider.complete = AsyncMock(side_effect=raise_exc)
    else:
        provider.complete = AsyncMock(
            return_value=CompletionResult(
                text=text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                model_name=model_name,
            )
        )

    provider.calculate_cost = MagicMock(return_value=Decimal("0.000001"))
    return provider


def _make_client(session: MagicMock, provider: MagicMock) -> TestClient:
    """Build a TestClient with dependency overrides injected."""

    async def override_get_db():
        yield session

    def override_get_provider_dep():
        return provider

    _test_app.dependency_overrides[get_db] = override_get_db
    _test_app.dependency_overrides[get_provider_dep] = override_get_provider_dep
    return TestClient(_test_app)


def _cleanup():
    _test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRouteEndpoint:
    def test_short_prompt_returns_200_with_full_response(self):
        """Simple prompt → 200 with all RouteResponse fields and correct model."""
        session = _make_mock_session("gemini-3.5-flash-lite")
        provider = _make_mock_provider()
        client = _make_client(session, provider)

        try:
            resp = client.post("/v1/route", json={"prompt": "Hi"})
        finally:
            _cleanup()

        assert resp.status_code == 200
        body = resp.json()
        assert body["model_name"] == "gemini-3.5-flash-lite"
        assert body["classifier_label"] == "simple"
        assert body["text"] == "Hello!"
        assert body["tokens_in"] == 10
        assert body["tokens_out"] == 5
        assert "request_id" in body
        assert "classifier_reason" in body
        assert "cost_usd" in body
        assert "latency_ms" in body

    def test_response_header_matches_body_request_id(self):
        """X-Request-ID header must equal body request_id."""
        session = _make_mock_session("gemini-3.5-flash-lite")
        provider = _make_mock_provider()
        client = _make_client(session, provider)

        try:
            resp = client.post("/v1/route", json={"prompt": "Hi"})
        finally:
            _cleanup()

        assert resp.status_code == 200
        body = resp.json()
        assert resp.headers["x-request-id"] == body["request_id"]

    def test_empty_prompt_returns_200(self):
        """Empty string prompt is valid — classifier handles it."""
        session = _make_mock_session("gemini-3.5-flash-lite")
        provider = _make_mock_provider()
        client = _make_client(session, provider)

        try:
            resp = client.post("/v1/route", json={"prompt": ""})
        finally:
            _cleanup()

        assert resp.status_code == 200

    def test_provider_value_error_returns_400(self):
        """Provider raising ValueError → 400 Bad Request."""
        session = _make_mock_session("gemini-3.5-flash-lite")
        provider = _make_mock_provider(raise_exc=ValueError("bad input"))
        client = _make_client(session, provider)

        try:
            resp = client.post("/v1/route", json={"prompt": "hello"})
        finally:
            _cleanup()

        assert resp.status_code == 400
        assert "bad input" in resp.json()["detail"]

    def test_provider_runtime_error_returns_500(self):
        """Provider raising RuntimeError → 500 Internal Server Error."""
        session = _make_mock_session("gemini-3.5-flash-lite")
        provider = _make_mock_provider(raise_exc=RuntimeError("crash"))
        client = _make_client(session, provider)

        try:
            resp = client.post("/v1/route", json={"prompt": "hello"})
        finally:
            _cleanup()

        assert resp.status_code == 500
        assert resp.json()["detail"] == "internal error"

    def test_missing_prompt_field_returns_422(self):
        """Missing required 'prompt' field → 422 Unprocessable Entity."""
        session = _make_mock_session()
        provider = _make_mock_provider()
        client = _make_client(session, provider)

        try:
            resp = client.post("/v1/route", json={"max_tokens": 512})
        finally:
            _cleanup()

        assert resp.status_code == 422
