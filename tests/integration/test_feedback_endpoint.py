"""Integration tests for POST /v1/feedback endpoint."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.feedback import router as feedback_router
from app.dependencies import get_db
from app.models.request import Request

_test_app = FastAPI()
_test_app.include_router(feedback_router, prefix="/v1")

_VALID_REQUEST_ID = "a1b2c3d4-e5f6-4890-abcd-ef1234567890"


def _make_mock_request_row(request_id: str = _VALID_REQUEST_ID) -> Request:
    row = MagicMock(spec=Request)
    row.request_id = request_id
    return row


def _make_quality_score_row(body_request_id: str) -> MagicMock:
    qs = MagicMock()
    qs.id = uuid.uuid4()
    qs.request_id = body_request_id
    qs.score = Decimal("4.50")
    qs.source = "human"
    qs.notes = None
    qs.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    return qs


def _make_found_session(request_id: str = _VALID_REQUEST_ID) -> MagicMock:
    """Session where request_id EXISTS — execute returns a row."""
    request_row = _make_mock_request_row(request_id)

    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = request_row

    session = MagicMock()
    session.execute = AsyncMock(return_value=scalar_result)
    session.add = MagicMock()
    session.commit = AsyncMock()

    qs_row = _make_quality_score_row(request_id)

    async def fake_refresh(obj):
        obj.id = qs_row.id
        obj.created_at = qs_row.created_at

    session.refresh = AsyncMock(side_effect=fake_refresh)
    return session


def _make_missing_session() -> MagicMock:
    """Session where request_id does NOT exist — execute returns nothing."""
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = None

    session = MagicMock()
    session.execute = AsyncMock(return_value=scalar_result)
    return session


def _make_client(session: MagicMock) -> TestClient:
    async def override_get_db():
        yield session

    _test_app.dependency_overrides[get_db] = override_get_db
    return TestClient(_test_app)


def _cleanup():
    _test_app.dependency_overrides.clear()


class TestFeedbackEndpoint:
    def test_valid_request_id_returns_201(self):
        """Valid feedback for an existing request_id → 201 with full response."""
        session = _make_found_session()
        client = _make_client(session)

        try:
            resp = client.post(
                "/v1/feedback",
                json={"request_id": _VALID_REQUEST_ID, "score": "4.50", "source": "human"},
            )
        finally:
            _cleanup()

        assert resp.status_code == 201
        body = resp.json()
        assert body["request_id"] == _VALID_REQUEST_ID
        assert body["source"] == "human"
        assert "id" in body
        assert "score" in body
        assert "created_at" in body

    def test_score_above_5_returns_422(self):
        """Score > 5 → 422 Unprocessable Entity (Pydantic validation)."""
        session = _make_found_session()
        client = _make_client(session)

        try:
            resp = client.post(
                "/v1/feedback",
                json={"request_id": _VALID_REQUEST_ID, "score": "5.01"},
            )
        finally:
            _cleanup()

        assert resp.status_code == 422

    def test_score_below_0_returns_422(self):
        """Score < 0 → 422 Unprocessable Entity (Pydantic validation)."""
        session = _make_found_session()
        client = _make_client(session)

        try:
            resp = client.post(
                "/v1/feedback",
                json={"request_id": _VALID_REQUEST_ID, "score": "-0.01"},
            )
        finally:
            _cleanup()

        assert resp.status_code == 422

    def test_unknown_request_id_returns_404(self):
        """request_id not in DB → 404 Not Found."""
        session = _make_missing_session()
        client = _make_client(session)

        try:
            resp = client.post(
                "/v1/feedback",
                json={"request_id": "00000000-0000-0000-0000-000000000000", "score": "3.00"},
            )
        finally:
            _cleanup()

        assert resp.status_code == 404
        assert resp.json()["detail"] == "request_id not found"

    def test_missing_request_id_field_returns_422(self):
        """Missing request_id field → 422 Unprocessable Entity."""
        session = _make_found_session()
        client = _make_client(session)

        try:
            resp = client.post("/v1/feedback", json={"score": "3.00"})
        finally:
            _cleanup()

        assert resp.status_code == 422

    def test_source_human_is_accepted(self):
        """source='human' is a valid literal value → 201."""
        session = _make_found_session()
        client = _make_client(session)

        try:
            resp = client.post(
                "/v1/feedback",
                json={"request_id": _VALID_REQUEST_ID, "score": "3.00", "source": "human"},
            )
        finally:
            _cleanup()

        assert resp.status_code == 201
        assert resp.json()["source"] == "human"

    def test_invalid_source_returns_422(self):
        """source not in Literal set → 422."""
        session = _make_found_session()
        client = _make_client(session)

        try:
            resp = client.post(
                "/v1/feedback",
                json={"request_id": _VALID_REQUEST_ID, "score": "3.00", "source": "robot"},
            )
        finally:
            _cleanup()

        assert resp.status_code == 422

    def test_notes_field_is_optional(self):
        """notes omitted → 201, notes is null in response."""
        session = _make_found_session()
        client = _make_client(session)

        try:
            resp = client.post(
                "/v1/feedback",
                json={"request_id": _VALID_REQUEST_ID, "score": "2.00"},
            )
        finally:
            _cleanup()

        assert resp.status_code == 201
        assert resp.json()["notes"] is None
