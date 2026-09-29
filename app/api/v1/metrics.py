"""Read-only endpoints for request history and metrics aggregates."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.windows import WINDOW_HOURS
from app.dependencies import get_db
from app.observability.logger import get_logger
from app.schemas.metrics import MetricsSummary, RequestListItem, RequestListResponse
from app.services import metrics_service

logger = get_logger("app.api.metrics")

router = APIRouter()


@router.get("/requests", response_model=RequestListResponse)
async def list_requests_endpoint(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    model: str | None = Query(None),
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> RequestListResponse:
    """Return a paginated list of logged requests.

    Args:
        limit: Maximum number of rows (1–200).
        offset: Number of rows to skip for pagination.
        model: Optional filter; only return rows for this model_name.
        session: Injected async DB session.

    Returns:
        RequestListResponse with pagination metadata and request rows.
    """
    logger.info(
        "list_requests",
        extra={"limit": limit, "offset": offset, "model": model},
    )

    total, rows = await metrics_service.list_requests(
        session=session,
        limit=limit,
        offset=offset,
        model_name=model,
    )

    items = [
        RequestListItem(
            request_id=r.request_id,
            model_name=r.model_name,
            classifier_label=r.classifier_label,
            tokens_in=r.tokens_in,
            tokens_out=r.tokens_out,
            cost_usd=r.cost_usd,
            latency_ms=r.latency_ms,
            status=r.status,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return RequestListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/metrics/summary", response_model=MetricsSummary)
async def metrics_summary_endpoint(
    window: str = Query("24h", pattern=r"^(1h|24h|7d|30d)$"),
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> MetricsSummary:
    """Return aggregated spend, latency, and quality metrics.

    Args:
        window: Time window — one of 1h, 24h, 7d, 30d.
        session: Injected async DB session.

    Returns:
        MetricsSummary with overall and per-model breakdowns.
    """
    logger.info("metrics_summary", extra={"window": window})

    window_hours = WINDOW_HOURS[window]
    return await metrics_service.metrics_summary(
        session=session, window_hours=window_hours
    )
