"""Pydantic schemas for the /v1/feedback endpoint."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    request_id: str = Field(..., description="The request_id (X-Request-ID) to score.")
    score: Decimal = Field(..., ge=0, le=5, description="Quality score 0.00 to 5.00.")
    source: Literal["human", "llm_judge", "heuristic"] = "human"
    notes: str | None = None


class FeedbackResponse(BaseModel):
    id: str
    request_id: str
    score: Decimal
    source: str
    notes: str | None
    created_at: datetime
