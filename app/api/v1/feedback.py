"""POST /v1/feedback — record a quality score for a past request."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.quality import QualityScore
from app.models.request import Request
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.security import require_api_key

logger = logging.getLogger("app.api.feedback")

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    body: FeedbackRequest,
    _: None = Depends(require_api_key),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> FeedbackResponse:
    """Record a quality score for a previously logged request.

    Args:
        body: FeedbackRequest with request_id, score, source, and optional notes.
        session: Injected async DB session.

    Returns:
        FeedbackResponse with the persisted quality score.

    Raises:
        HTTPException 404: If request_id does not exist in the requests table.
    """
    result = await session.execute(
        select(Request).where(Request.request_id == body.request_id)
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        logger.warning("feedback_not_found", extra={"request_id": body.request_id})
        raise HTTPException(status_code=404, detail="request_id not found")

    qs = QualityScore(
        request_id=body.request_id,
        score=body.score,
        source=body.source,
        notes=body.notes,
    )
    session.add(qs)
    await session.commit()
    await session.refresh(qs)

    logger.info(
        "feedback_recorded",
        extra={
            "request_id": body.request_id,
            "score": str(body.score),
            "source": body.source,
        },
    )

    return FeedbackResponse(
        id=str(qs.id),
        request_id=qs.request_id,
        score=qs.score,
        source=qs.source,
        notes=qs.notes,
        created_at=qs.created_at,
    )
