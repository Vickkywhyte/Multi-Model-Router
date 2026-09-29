"""Integration tests for POST /v1/route endpoint."""

# Minimal test app is built per-test via client_factory fixture in conftest.py.
# No tracing middleware is added, so X-Request-ID header is set only by the
# route handler — which is what test_response_header_matches_body_request_id checks.


class TestRouteEndpoint:
    def test_short_prompt_returns_200_with_full_response(
        self, mock_session, mock_provider, client_factory
    ):
        """Simple prompt → 200 with all RouteResponse fields and correct model."""
        session = mock_session()
        provider = mock_provider()
        with client_factory(session, provider) as client:
            resp = client.post("/v1/route", json={"prompt": "Hi"})

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

    def test_response_header_matches_body_request_id(
        self, mock_session, mock_provider, client_factory
    ):
        """X-Request-ID header must equal body request_id."""
        session = mock_session()
        provider = mock_provider()
        with client_factory(session, provider) as client:
            resp = client.post("/v1/route", json={"prompt": "Hi"})

        assert resp.status_code == 200
        body = resp.json()
        assert resp.headers["x-request-id"] == body["request_id"]

    def test_empty_prompt_returns_200(self, mock_session, mock_provider, client_factory):
        """Empty string prompt is valid — classifier handles it."""
        session = mock_session()
        provider = mock_provider()
        with client_factory(session, provider) as client:
            resp = client.post("/v1/route", json={"prompt": ""})

        assert resp.status_code == 200

    def test_provider_value_error_returns_400(
        self, mock_session, mock_provider, client_factory
    ):
        """Provider raising ValueError → 400 Bad Request."""
        session = mock_session()
        provider = mock_provider(raise_exc=ValueError("bad input"))
        with client_factory(session, provider) as client:
            resp = client.post("/v1/route", json={"prompt": "hello"})

        assert resp.status_code == 400
        assert "bad input" in resp.json()["detail"]

    def test_provider_runtime_error_returns_500(
        self, mock_session, mock_provider, client_factory
    ):
        """Provider raising RuntimeError → 500 Internal Server Error."""
        session = mock_session()
        provider = mock_provider(raise_exc=RuntimeError("crash"))
        with client_factory(session, provider) as client:
            resp = client.post("/v1/route", json={"prompt": "hello"})

        assert resp.status_code == 500
        assert resp.json()["detail"] == "internal error"

    def test_missing_prompt_field_returns_422(
        self, mock_session, mock_provider, client_factory
    ):
        """Missing required 'prompt' field → 422 Unprocessable Entity."""
        session = mock_session()
        provider = mock_provider()
        with client_factory(session, provider) as client:
            resp = client.post("/v1/route", json={"max_tokens": 512})

        assert resp.status_code == 422
