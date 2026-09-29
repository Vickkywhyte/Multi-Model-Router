"""Unit tests for app/services/metrics_service.py and app/core/windows.py."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.windows import hours_to_label
from app.services.metrics_service import metrics_summary

# ---------------------------------------------------------------------------
# hours_to_label
# ---------------------------------------------------------------------------


def test_hours_to_label_known_windows() -> None:
    assert hours_to_label(1) == "1h"
    assert hours_to_label(24) == "24h"
    assert hours_to_label(168) == "7d"
    assert hours_to_label(720) == "30d"


def test_hours_to_label_unknown_returns_fallback() -> None:
    assert hours_to_label(999) == "999h"
    assert hours_to_label(0) == "0h"


# ---------------------------------------------------------------------------
# metrics_summary — empty window (no requests)
# ---------------------------------------------------------------------------


def _make_empty_session() -> MagicMock:
    """Return a mock session where both queries return zero-row results."""
    # Overall aggregate row: all zeros, no rows in per-model
    overall_row = MagicMock()
    overall_row.total_requests = 0
    overall_row.total_cost_usd = Decimal("0")
    overall_row.avg_latency_ms = 0.0
    overall_row.error_count = 0

    overall_result = MagicMock()
    overall_result.one.return_value = overall_row

    per_model_result = MagicMock()
    per_model_result.all.return_value = []

    session = MagicMock()
    session.execute = AsyncMock(side_effect=[overall_result, per_model_result])
    return session


@pytest.mark.asyncio
async def test_metrics_summary_empty_window_returns_zeros() -> None:
    """metrics_summary with no requests returns a valid MetricsSummary with zeros."""
    session = _make_empty_session()

    result = await metrics_summary(session=session, window_hours=24)

    assert result.total_requests == 0
    assert result.total_cost_usd == Decimal("0")
    assert result.avg_latency_ms == 0.0
    assert result.error_count == 0
    assert result.by_model == []
    assert result.window == "24h"
    assert isinstance(result.since, datetime)


@pytest.mark.asyncio
async def test_metrics_summary_null_percentiles_default_to_zero() -> None:
    """percentile_cont returning NULL (empty set) is coerced to 0, not a TypeError."""
    overall_row = MagicMock()
    overall_row.total_requests = 1
    overall_row.total_cost_usd = Decimal("0.001")
    overall_row.avg_latency_ms = 500.0
    overall_row.error_count = 0

    overall_result = MagicMock()
    overall_result.one.return_value = overall_row

    model_row = MagicMock()
    model_row.model_name = "gemini-3.5-flash-lite"
    model_row.request_count = 1
    model_row.total_cost_usd = Decimal("0.001")
    model_row.avg_cost_usd = Decimal("0.001")
    model_row.avg_latency_ms = 500.0
    model_row.p50_latency_ms = None  # NULL from percentile_cont on empty set
    model_row.p95_latency_ms = None
    model_row.total_tokens_in = 100
    model_row.total_tokens_out = 50
    model_row.avg_quality_score = None

    per_model_result = MagicMock()
    per_model_result.all.return_value = [model_row]

    session = MagicMock()
    session.execute = AsyncMock(side_effect=[overall_result, per_model_result])

    result = await metrics_summary(session=session, window_hours=24)

    assert len(result.by_model) == 1
    model = result.by_model[0]
    assert model.p50_latency_ms == 0
    assert model.p95_latency_ms == 0
