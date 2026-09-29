"""Routing service — classify, pick model, call provider, log to DB."""

import hashlib
from decimal import Decimal
from time import perf_counter
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.classifier import classify
from app.core.pricing import tier_to_model
from app.models.model import Model
from app.models.request import Request
from app.observability.logger import get_logger
from app.providers.base import BaseProvider, CompletionRequest
from app.schemas.route import RouteRequest, RouteResponse

logger = get_logger("app.services.routing")


async def route_prompt(
    request: RouteRequest,
    session: AsyncSession,
    provider: BaseProvider,
) -> RouteResponse:
    """Classify a prompt, call the appropriate model, log the result, and return.

    Args:
        request: The incoming prompt and generation parameters.
        session: An open async SQLAlchemy session.
        provider: The LLM provider adapter to use.

    Returns:
        RouteResponse with completion text, token counts, cost, and metadata.

    Raises:
        Exception: Re-raises any exception from the provider after logging it.
    """
    request_id = str(uuid4())
    start = perf_counter()

    classification = classify(request.prompt)
    model_name = tier_to_model(classification.label)

    prompt_hash = hashlib.sha256(request.prompt.encode()).hexdigest()

    try:
        completion = await provider.complete(
            CompletionRequest(
                prompt=request.prompt,
                model_name=model_name,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
        )
    except Exception as exc:
        latency_ms = int((perf_counter() - start) * 1000)
        logger.error(
            "Provider error",
            extra={
                "request_id": request_id,
                "model_name": model_name,
                "error": str(exc),
                "latency_ms": latency_ms,
            },
        )
        await _persist_request(
            session=session,
            request_id=request_id,
            prompt_hash=prompt_hash,
            prompt_text=request.prompt,
            classification_label=classification.label,
            classification_reason=classification.reason,
            model_name=model_name,
            tokens_in=0,
            tokens_out=0,
            cost_usd=Decimal("0"),
            latency_ms=latency_ms,
            status="error",
            error_message=str(exc),
        )
        raise

    latency_ms = int((perf_counter() - start) * 1000)
    cost_usd = provider.calculate_cost(
        model_name, completion.tokens_in, completion.tokens_out
    )

    await _persist_request(
        session=session,
        request_id=request_id,
        prompt_hash=prompt_hash,
        prompt_text=request.prompt,
        classification_label=classification.label,
        classification_reason=classification.reason,
        model_name=model_name,
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        status="success",
        error_message=None,
    )

    logger.info(
        "Request routed",
        extra={
            "request_id": request_id,
            "model_name": model_name,
            "label": classification.label,
            "tokens_in": completion.tokens_in,
            "tokens_out": completion.tokens_out,
            "cost_usd": str(cost_usd),
            "latency_ms": latency_ms,
        },
    )

    return RouteResponse(
        request_id=request_id,
        model_name=model_name,
        classifier_label=classification.label,
        classifier_reason=classification.reason,
        text=completion.text,
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )


async def _persist_request(
    *,
    session: AsyncSession,
    request_id: str,
    prompt_hash: str,
    prompt_text: str,
    classification_label: str,
    classification_reason: str,
    model_name: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: Decimal,
    latency_ms: int,
    status: str,
    error_message: str | None,
) -> None:
    """Insert a Request row; swallows DB errors so they don't break the response.

    Args:
        session: Active async session.
        All other args map directly to Request columns.
    """
    try:
        result = await session.execute(select(Model).where(Model.name == model_name))
        model_row = result.scalar_one_or_none()

        if model_row is None:
            logger.warning(
                "Model row not found in DB; skipping DB insert",
                extra={"model_name": model_name},
            )
            return

        row = Request(
            request_id=request_id,
            prompt_hash=prompt_hash,
            prompt_text=prompt_text,
            classifier_label=classification_label,
            classifier_reason=classification_reason,
            model_id=model_row.id,
            model_name=model_name,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )
        session.add(row)
        await session.commit()
    except Exception as db_exc:
        logger.error(
            "DB persist failed",
            extra={"request_id": request_id, "error": str(db_exc)},
        )
