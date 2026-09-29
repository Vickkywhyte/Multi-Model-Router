"""Route endpoint — POST /v1/route classifies and routes a prompt."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.providers.base import BaseProvider
from app.providers.factory import get_provider
from app.schemas.route import RouteRequest, RouteResponse
from app.services.routing_service import route_prompt

router = APIRouter(tags=["route"])
logger = logging.getLogger("app.api.route")


def get_provider_dep() -> BaseProvider:
    return get_provider("google")


@router.post("/route", response_model=RouteResponse, status_code=200)
async def route(
    payload: RouteRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    provider: BaseProvider = Depends(get_provider_dep),  # noqa: B008
) -> RouteResponse:
    """Classify a prompt and route it to the appropriate Gemini model.

    Args:
        payload: The prompt and generation parameters.
        response: FastAPI response object (used to set headers).
        session: Async DB session from dependency injection.
        provider: LLM provider adapter from dependency injection.

    Returns:
        RouteResponse with completion text, token counts, cost, and metadata.

    Raises:
        HTTPException 400: If route_prompt raises ValueError.
        HTTPException 500: For any other exception.
    """
    logger.info("Received route request", extra={"prompt_len": len(payload.prompt)})
    try:
        result = await route_prompt(payload, session, provider)
        response.headers["X-Request-ID"] = result.request_id
        return result
    except ValueError as exc:
        logger.warning("Bad request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("route_prompt failed")
        raise HTTPException(status_code=500, detail="internal error") from exc
