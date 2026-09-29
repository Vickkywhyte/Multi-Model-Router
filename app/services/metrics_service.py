"""Service layer for metrics and request-list aggregations.

All heavy lifting is done in SQL via SQLAlchemy 2.0 async ORM so Python never
holds full result-sets in memory for aggregation.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import QualityScore
from app.models.request import Request
from app.observability.logger import get_logger
from app.schemas.metrics import MetricsSummary, ModelMetrics

logger = get_logger("app.services.metrics")

_WINDOW_MAP: dict[str, int] = {
    "1h": 1,
    "24h": 24,
    "7d": 168,
    "30d": 720,
}


async def list_requests(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    model_name: str | None = None,
) -> tuple[int, list[Request]]:
    """Return a paginated list of logged requests ordered by created_at DESC.

    Args:
        session: Async database session.
        limit: Maximum rows to return.
        offset: Number of rows to skip.
        model_name: Optional filter on model_name column.

    Returns:
        Tuple of (total_count, rows).
    """
    base = select(Request)
    count_q = select(func.count()).select_from(Request)

    if model_name is not None:
        base = base.where(Request.model_name == model_name)
        count_q = count_q.where(Request.model_name == model_name)

    total_result = await session.execute(count_q)
    total = total_result.scalar_one()

    rows_result = await session.execute(
        base.order_by(Request.created_at.desc()).limit(limit).offset(offset)
    )
    rows = list(rows_result.scalars().all())

    logger.debug(
        "list_requests",
        extra={
            "total": total,
            "limit": limit,
            "offset": offset,
            "model_name": model_name,
        },
    )
    return total, rows


async def metrics_summary(
    session: AsyncSession,
    window_hours: int = 24,
) -> MetricsSummary:
    """Compute aggregated metrics for requests in the given time window.

    Args:
        session: Async database session.
        window_hours: How many hours back to look from now.

    Returns:
        MetricsSummary populated from SQL aggregations.
    """
    since = datetime.now(tz=UTC) - timedelta(hours=window_hours)
    window_label = _hours_to_label(window_hours)

    # --- Overall aggregates ---
    overall_q = select(
        func.count().label("total_requests"),
        func.coalesce(func.sum(Request.cost_usd), 0).label("total_cost_usd"),
        func.coalesce(func.avg(Request.latency_ms), 0).label("avg_latency_ms"),
        func.count()
        .filter(Request.status != "success")
        .label("error_count"),
    ).where(Request.created_at >= since)

    overall_row = (await session.execute(overall_q)).one()
    total_requests: int = overall_row.total_requests
    total_cost_usd = Decimal(str(overall_row.total_cost_usd))
    avg_latency_ms = float(overall_row.avg_latency_ms)
    error_count: int = overall_row.error_count

    # --- Per-model aggregates with percentile_cont ---
    # Left-join quality_scores so avg_quality_score is NULL when there's no feedback.
    per_model_q = (
        select(
            Request.model_name,
            func.count().label("request_count"),
            func.coalesce(func.sum(Request.cost_usd), 0).label("total_cost_usd"),
            func.coalesce(func.avg(Request.cost_usd), 0).label("avg_cost_usd"),
            func.coalesce(func.avg(Request.latency_ms), 0).label("avg_latency_ms"),
            func.percentile_cont(0.5)
            .within_group(Request.latency_ms)
            .label("p50_latency_ms"),
            func.percentile_cont(0.95)
            .within_group(Request.latency_ms)
            .label("p95_latency_ms"),
            func.coalesce(func.sum(Request.tokens_in), 0).label("total_tokens_in"),
            func.coalesce(func.sum(Request.tokens_out), 0).label("total_tokens_out"),
            func.avg(QualityScore.score).label("avg_quality_score"),
        )
        .outerjoin(QualityScore, Request.request_id == QualityScore.request_id)
        .where(Request.created_at >= since)
        .group_by(Request.model_name)
        .order_by(Request.model_name)
    )

    per_model_rows = (await session.execute(per_model_q)).all()

    by_model: list[ModelMetrics] = []
    for row in per_model_rows:
        avg_q = (
            Decimal(str(row.avg_quality_score))
            if row.avg_quality_score is not None
            else None
        )
        by_model.append(
            ModelMetrics(
                model_name=row.model_name,
                request_count=row.request_count,
                total_cost_usd=Decimal(str(row.total_cost_usd)),
                avg_cost_usd=Decimal(str(row.avg_cost_usd)),
                avg_latency_ms=float(row.avg_latency_ms),
                p50_latency_ms=int(row.p50_latency_ms),
                p95_latency_ms=int(row.p95_latency_ms),
                total_tokens_in=int(row.total_tokens_in),
                total_tokens_out=int(row.total_tokens_out),
                avg_quality_score=avg_q,
            )
        )

    logger.info(
        "metrics_summary",
        extra={
            "window": window_label,
            "total_requests": total_requests,
            "models": len(by_model),
        },
    )

    return MetricsSummary(
        window=window_label,
        since=since,
        total_requests=total_requests,
        total_cost_usd=total_cost_usd,
        avg_latency_ms=avg_latency_ms,
        error_count=error_count,
        by_model=by_model,
    )


def _hours_to_label(hours: int) -> str:
    """Convert an hour count back to the canonical window label string."""
    reverse = {v: k for k, v in _WINDOW_MAP.items()}
    return reverse.get(hours, f"{hours}h")
