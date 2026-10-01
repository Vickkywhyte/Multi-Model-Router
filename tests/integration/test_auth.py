"""Integration tests for X-API-Key authentication on protected endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import metrics as metrics_module
from app.api.v1 import route as route_module
from app.api.v1.route import get_provider_dep
from app.dependencies import get_db, get_redis
from tests.conftest import _TEST_API_KEY

_AUTH = {"X-API-Key": _TEST_API_KEY}


@pytest.fixture
def auth_client(mock_session, mock_provider, mock_redis):
    """Minimal FastAPI app with /health, /v1/route, and /v1/metrics/summary."""
    session = mock_session()
    provider = mock_provider()
    redis = mock_redis()

    app = FastAPI()
    app.include_router(route_module.router, prefix="/v1")
    app.include_router(metrics_module.router, prefix="/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    async def override_get_db():
        yield session

    async def override_get_redis():
        yield redis

    def override_get_provider_dep():
        return provider

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_provider_dep] = override_get_provider_dep

    with TestClient(app) as client:
        yield client


class TestApiKeyAuth:
    def test_post_route_without_key_returns_401(self, auth_client):
        """Missing X-API-Key header on POST /v1/route → 401."""
        resp = auth_client.post("/v1/route", json={"prompt": "hi"})
        assert resp.status_code == 401

    def test_post_route_with_wrong_key_returns_401(self, auth_client):
        """Incorrect X-API-Key on POST /v1/route → 401."""
        resp = auth_client.post(
            "/v1/route",
            json={"prompt": "hi"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_post_route_with_correct_key_returns_200(self, auth_client):
        """Valid X-API-Key on POST /v1/route → 200."""
        resp = auth_client.post("/v1/route", json={"prompt": "hi"}, headers=_AUTH)
        assert resp.status_code == 200

    def test_get_health_requires_no_key(self, auth_client):
        """GET /health works without any authentication header."""
        resp = auth_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_get_metrics_summary_requires_no_key(self, auth_client):
        """GET /v1/metrics/summary works without any authentication header."""
        from datetime import UTC, datetime
        from decimal import Decimal
        from unittest.mock import AsyncMock, patch

        from app.schemas.metrics import MetricsSummary

        stub = MetricsSummary(
            window="24h",
            since=datetime.now(tz=UTC),
            total_requests=0,
            total_cost_usd=Decimal("0"),
            avg_latency_ms=0.0,
            error_count=0,
            by_model=[],
        )
        with patch(
            "app.api.v1.metrics.metrics_service.metrics_summary",
            new=AsyncMock(return_value=stub),
        ):
            resp = auth_client.get("/v1/metrics/summary")
        assert resp.status_code == 200
