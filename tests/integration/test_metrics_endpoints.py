"""Integration tests for GET /v1/requests and GET /v1/metrics/summary."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.metrics import router as metrics_router
from app.dependencies import get_db
from app.schemas.metrics import (
    MetricsSummary,
    ModelMetrics,
    RequestListItem,
    RequestListResponse,
)

# ---------------------------------------------------------------------------
# Shared test app
# ---------------------------------------------------------------------------

_test_app = FastAPI()
_test_app.include_router(metrics_router, prefix="/v1")


def _make_session() -> MagicMock:
    """Return a minimal mock AsyncSession — services are patched at the module level."""
    session = MagicMock()
    return session


def _make_client(session: MagicMock | None = None) -> TestClient:
    if session is None:
        session = _make_session()

    async def override_get_db():
        yield session

    _test_app.dependency_overrides[get_db] = override_get_db
    return TestClient(_test_app)


def _cleanup():
    _test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Canned fixtures
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 9, 29, 12, 0, 0, tzinfo=UTC)

_ITEM = RequestListItem(
    request_id="req-abc-123",
    model_name="gemini-3.5-flash-lite",
    classifier_label="simple",
    tokens_in=10,
    tokens_out=5,
    cost_usd=Decimal("0.000003"),
    latency_ms=250,
    status="success",
    created_at=_NOW,
)

_LIST_RESPONSE = RequestListResponse(
    total=1,
    limit=50,
    offset=0,
    items=[_ITEM],
)

_MODEL_METRICS = ModelMetrics(
    model_name="gemini-3.5-flash-lite",
    request_count=1,
    total_cost_usd=Decimal("0.000003"),
    avg_cost_usd=Decimal("0.000003"),
    avg_latency_ms=250.0,
    p50_latency_ms=250,
    p95_latency_ms=250,
    total_tokens_in=10,
    total_tokens_out=5,
    avg_quality_score=None,
)

_SUMMARY = MetricsSummary(
    window="24h",
    since=_NOW,
    total_requests=1,
    total_cost_usd=Decimal("0.000003"),
    avg_latency_ms=250.0,
    error_count=0,
    by_model=[_MODEL_METRICS],
)


# ---------------------------------------------------------------------------
# Tests: GET /v1/requests
# ---------------------------------------------------------------------------


class TestListRequestsEndpoint:
    def test_returns_200_with_pagination_shape(self):
        """Basic call returns 200 and a valid RequestListResponse."""
        client = _make_client()
        try:
            with patch(
                "app.api.v1.metrics.metrics_service.list_requests",
                new=AsyncMock(return_value=(1, [])),
            ):
                resp = client.get("/v1/requests")
        finally:
            _cleanup()

        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert "items" in body
        assert body["total"] == 1
        assert body["limit"] == 50
        assert body["offset"] == 0

    def test_returns_items_when_rows_present(self):
        """Service returning one row yields one serialised item."""

        from app.models.request import Request

        row = MagicMock(spec=Request)
        row.request_id = "req-abc-123"
        row.model_name = "gemini-3.5-flash-lite"
        row.classifier_label = "simple"
        row.tokens_in = 10
        row.tokens_out = 5
        row.cost_usd = Decimal("0.000003")
        row.latency_ms = 250
        row.status = "success"
        row.created_at = _NOW

        client = _make_client()
        try:
            with patch(
                "app.api.v1.metrics.metrics_service.list_requests",
                new=AsyncMock(return_value=(1, [row])),
            ):
                resp = client.get("/v1/requests")
        finally:
            _cleanup()

        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["request_id"] == "req-abc-123"
        assert items[0]["model_name"] == "gemini-3.5-flash-lite"

    def test_limit_and_offset_passed_to_service(self):
        """Query params limit and offset are forwarded to list_requests."""
        mock_fn = AsyncMock(return_value=(0, []))
        client = _make_client()
        try:
            with patch("app.api.v1.metrics.metrics_service.list_requests", new=mock_fn):
                client.get("/v1/requests?limit=10&offset=5")
        finally:
            _cleanup()

        mock_fn.assert_awaited_once()
        _, kwargs = mock_fn.call_args
        assert kwargs["limit"] == 10
        assert kwargs["offset"] == 5

    def test_model_filter_passed_to_service(self):
        """?model= query param is forwarded as model_name to list_requests."""
        mock_fn = AsyncMock(return_value=(0, []))
        client = _make_client()
        try:
            with patch("app.api.v1.metrics.metrics_service.list_requests", new=mock_fn):
                client.get("/v1/requests?model=gemini-3.5-flash")
        finally:
            _cleanup()

        mock_fn.assert_awaited_once()
        _, kwargs = mock_fn.call_args
        assert kwargs["model_name"] == "gemini-3.5-flash"

    def test_limit_above_200_returns_422(self):
        """limit > 200 is rejected by FastAPI query validation."""
        client = _make_client()
        try:
            with patch(
                "app.api.v1.metrics.metrics_service.list_requests",
                new=AsyncMock(return_value=(0, [])),
            ):
                resp = client.get("/v1/requests?limit=999")
        finally:
            _cleanup()

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests: GET /v1/metrics/summary
# ---------------------------------------------------------------------------


class TestMetricsSummaryEndpoint:
    def test_returns_200_with_all_fields(self):
        """Summary endpoint returns 200 and a fully-populated MetricsSummary."""
        client = _make_client()
        try:
            with patch(
                "app.api.v1.metrics.metrics_service.metrics_summary",
                new=AsyncMock(return_value=_SUMMARY),
            ):
                resp = client.get("/v1/metrics/summary?window=24h")
        finally:
            _cleanup()

        assert resp.status_code == 200
        body = resp.json()
        assert body["window"] == "24h"
        assert body["total_requests"] == 1
        assert body["error_count"] == 0
        assert len(body["by_model"]) == 1
        assert body["by_model"][0]["model_name"] == "gemini-3.5-flash-lite"
        assert body["by_model"][0]["avg_quality_score"] is None

    def test_window_7d_passes_correct_hours(self):
        """?window=7d passes window_hours=168 to the service."""
        mock_fn = AsyncMock(return_value=_SUMMARY)
        client = _make_client()
        try:
            with patch("app.api.v1.metrics.metrics_service.metrics_summary", new=mock_fn):
                client.get("/v1/metrics/summary?window=7d")
        finally:
            _cleanup()

        mock_fn.assert_awaited_once()
        _, kwargs = mock_fn.call_args
        assert kwargs["window_hours"] == 168

    def test_invalid_window_returns_422(self):
        """?window=invalid is rejected by FastAPI pattern validation."""
        client = _make_client()
        try:
            with patch(
                "app.api.v1.metrics.metrics_service.metrics_summary",
                new=AsyncMock(return_value=_SUMMARY),
            ):
                resp = client.get("/v1/metrics/summary?window=invalid")
        finally:
            _cleanup()

        assert resp.status_code == 422

    def test_default_window_is_24h(self):
        """Omitting ?window= uses the 24h default."""
        mock_fn = AsyncMock(return_value=_SUMMARY)
        client = _make_client()
        try:
            with patch("app.api.v1.metrics.metrics_service.metrics_summary", new=mock_fn):
                client.get("/v1/metrics/summary")
        finally:
            _cleanup()

        mock_fn.assert_awaited_once()
        _, kwargs = mock_fn.call_args
        assert kwargs["window_hours"] == 24
