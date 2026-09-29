"""ORM model for the 'quality_scores' table — human or automated quality ratings."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QualityScore(Base):
    """A quality rating attached to a logged request."""

    __tablename__ = "quality_scores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("requests.request_id"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
