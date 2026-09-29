"""Integration tests for GET /v1/requests and GET /v1/metrics/summary."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.schemas.metrics import (
    MetricsSummary,
    ModelMetrics,
    RequestListItem,
    RequestListResponse,
)

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
    def test_returns_200_with_pagination_shape(self, mock_session, client_factory):
        """Basic call returns 200 and a valid RequestListResponse."""
        session = mock_session()
        with client_factory(session) as client, patch(
            "app.api.v1.metrics.metrics_service.list_requests",
            new=AsyncMock(return_value=(1, [])),
        ):
            resp = client.get("/v1/requests")

        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert "items" in body
        assert body["total"] == 1
        assert body["limit"] == 50
        assert body["offset"] == 0

    def test_returns_items_when_rows_present(self, mock_session, client_factory):
        """Service returning one row yields one serialised item."""
        from unittest.mock import MagicMock

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

        session = mock_session()
        with client_factory(session) as client, patch(
            "app.api.v1.metrics.metrics_service.list_requests",
            new=AsyncMock(return_value=(1, [row])),
        ):
            resp = client.get("/v1/requests")

        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["request_id"] == "req-abc-123"
        assert items[0]["model_name"] == "gemini-3.5-flash-lite"

    def test_limit_and_offset_passed_to_service(self, mock_session, client_factory):
        """Query params limit and offset are forwarded to list_requests."""
        mock_fn = AsyncMock(return_value=(0, []))
        session = mock_session()
        with client_factory(session) as client, patch(
            "app.api.v1.metrics.metrics_service.list_requests", new=mock_fn
        ):
            client.get("/v1/requests?limit=10&offset=5")

        mock_fn.assert_awaited_once()
        _, kwargs = mock_fn.call_args
        assert kwargs["limit"] == 10
        assert kwargs["offset"] == 5

    def test_model_filter_passed_to_service(self, mock_session, client_factory):
        """?model= query param is forwarded as model_name to list_requests."""
        mock_fn = AsyncMock(return_value=(0, []))
        session = mock_session()
        with client_factory(session) as client, patch(
            "app.api.v1.metrics.metrics_service.list_requests", new=mock_fn
        ):
            client.get("/v1/requests?model=gemini-3.5-flash")

        mock_fn.assert_awaited_once()
        _, kwargs = mock_fn.call_args
        assert kwargs["model_name"] == "gemini-3.5-flash"

    def test_limit_above_200_returns_422(self, mock_session, client_factory):
        """limit > 200 is rejected by FastAPI query validation."""
        session = mock_session()
        with client_factory(session) as client, patch(
            "app.api.v1.metrics.metrics_service.list_requests",
            new=AsyncMock(return_value=(0, [])),
        ):
            resp = client.get("/v1/requests?limit=999")

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests: GET /v1/metrics/summary
# ---------------------------------------------------------------------------


class TestMetricsSummaryEndpoint:
    def test_returns_200_with_all_fields(self, mock_session, client_factory):
        """Summary endpoint returns 200 and a fully-populated MetricsSummary."""
        session = mock_session()
        with client_factory(session) as client, patch(
            "app.api.v1.metrics.metrics_service.metrics_summary",
            new=AsyncMock(return_value=_SUMMARY),
        ):
            resp = client.get("/v1/metrics/summary?window=24h")

        assert resp.status_code == 200
        body = resp.json()
        assert body["window"] == "24h"
        assert body["total_requests"] == 1
        assert body["error_count"] == 0
        assert len(body["by_model"]) == 1
        assert body["by_model"][0]["model_name"] == "gemini-3.5-flash-lite"
        assert body["by_model"][0]["avg_quality_score"] is None

    def test_window_7d_passes_correct_hours(self, mock_session, client_factory):
        """?window=7d passes window_hours=168 to the service."""
        mock_fn = AsyncMock(return_value=_SUMMARY)
        session = mock_session()
        with client_factory(session) as client, patch(
            "app.api.v1.metrics.metrics_service.metrics_summary", new=mock_fn
        ):
            client.get("/v1/metrics/summary?window=7d")

        mock_fn.assert_awaited_once()
        _, kwargs = mock_fn.call_args
        assert kwargs["window_hours"] == 168

    def test_invalid_window_returns_422(self, mock_session, client_factory):
        """?window=invalid is rejected by FastAPI pattern validation."""
        session = mock_session()
        with client_factory(session) as client, patch(
            "app.api.v1.metrics.metrics_service.metrics_summary",
            new=AsyncMock(return_value=_SUMMARY),
        ):
            resp = client.get("/v1/metrics/summary?window=invalid")

        assert resp.status_code == 422

    def test_default_window_is_24h(self, mock_session, client_factory):
        """Omitting ?window= uses the 24h default."""
        mock_fn = AsyncMock(return_value=_SUMMARY)
        session = mock_session()
        with client_factory(session) as client, patch(
            "app.api.v1.metrics.metrics_service.metrics_summary", new=mock_fn
        ):
            client.get("/v1/metrics/summary")

        mock_fn.assert_awaited_once()
        _, kwargs = mock_fn.call_args
        assert kwargs["window_hours"] == 24
