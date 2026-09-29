"""Pydantic v2 schemas for the /v1/requests and /v1/metrics endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class RequestListItem(BaseModel):
    """A single row returned by the paginated request list."""

    request_id: str
    model_name: str
    classifier_label: Literal["simple", "medium", "complex"]
    tokens_in: int
    tokens_out: int
    cost_usd: Decimal
    latency_ms: int
    status: str
    created_at: datetime


class RequestListResponse(BaseModel):
    """Paginated list of logged requests."""

    total: int
    limit: int
    offset: int
    items: list[RequestListItem]


class ModelMetrics(BaseModel):
    """Aggregated metrics for a single model over the reporting window."""

    model_name: str
    request_count: int
    total_cost_usd: Decimal
    avg_cost_usd: Decimal
    avg_latency_ms: float
    p50_latency_ms: int
    p95_latency_ms: int
    total_tokens_in: int
    total_tokens_out: int
    avg_quality_score: Decimal | None  # None if no feedback rows yet


class MetricsSummary(BaseModel):
    """Overall metrics summary for the reporting window."""

    window: str  # e.g. "24h"
    since: datetime
    total_requests: int
    total_cost_usd: Decimal
    avg_latency_ms: float
    error_count: int
    by_model: list[ModelMetrics]
