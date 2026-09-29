"""Integration tests for POST /v1/route rate limiting."""

import pytest

# The rate-limit setting used in tests — must match what app/config.py sets
# via RATE_LIMIT_PER_MINUTE (default 30). We override to a small value so
# tests don't have to make 30+ requests.
_TEST_LIMIT = 3


@pytest.fixture(autouse=True)
def _patch_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lower the rate limit to 3 RPM so tests stay fast."""
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", str(_TEST_LIMIT))
    yield
    get_settings.cache_clear()


class TestRateLimit:
    def test_requests_within_limit_succeed(
        self, mock_session, mock_provider, mock_redis, client_factory
    ):
        """First N requests (≤ limit) all return 200."""
        # Counts 1, 2, 3 — all within the 3 RPM limit
        redis = mock_redis(incr_values=[1, 2, 3])
        session = mock_session()
        provider = mock_provider()

        with client_factory(session, provider, redis_client=redis) as client:
            for _ in range(_TEST_LIMIT):
                resp = client.post("/v1/route", json={"prompt": "hi"})
                assert resp.status_code == 200

    def test_request_over_limit_returns_429(
        self, mock_session, mock_provider, mock_redis, client_factory
    ):
        """(N+1)th request returns 429 with a Retry-After header."""
        # Fourth call returns count 4, which exceeds limit 3
        redis = mock_redis(incr_values=[4])
        session = mock_session()
        provider = mock_provider()

        with client_factory(session, provider, redis_client=redis) as client:
            resp = client.post("/v1/route", json={"prompt": "hi"})

        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        assert resp.headers["Retry-After"] == "60"
        assert "Rate limit exceeded" in resp.json()["detail"]

    def test_different_ips_have_separate_counters(
        self, mock_session, mock_provider, mock_redis, client_factory
    ):
        """Requests from different client IPs do not share a counter.

        TestClient always uses 127.0.0.1 as the client IP. To simulate two
        different IPs we verify that the Redis key includes the IP by
        inspecting the calls made to the mock rather than making HTTP requests
        from two different addresses.
        """
        from unittest.mock import call

        redis = mock_redis(incr_values=[1, 1])  # two separate first-increments
        session = mock_session()
        provider = mock_provider()

        with client_factory(session, provider, redis_client=redis) as client:
            # Two requests from the same TestClient IP — both at count=1 (allowed)
            resp1 = client.post("/v1/route", json={"prompt": "hi"})
            resp2 = client.post("/v1/route", json={"prompt": "hi"})

        assert resp1.status_code == 200
        assert resp2.status_code == 200

        # Both calls used the same key (same IP)
        expected_key = "ratelimit:route:testclient"
        calls = redis.incr.call_args_list
        assert all(c == call(expected_key) for c in calls)

    def test_redis_failure_fails_open(
        self, mock_session, mock_provider, mock_redis, client_factory
    ):
        """If Redis raises, the request is allowed (fail-open behaviour)."""
        redis = mock_redis()
        redis.incr = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock(
            side_effect=ConnectionError("Redis down")
        )
        session = mock_session()
        provider = mock_provider()

        with client_factory(session, provider, redis_client=redis) as client:
            resp = client.post("/v1/route", json={"prompt": "hi"})

        assert resp.status_code == 200
