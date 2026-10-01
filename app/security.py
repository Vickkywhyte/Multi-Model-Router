"""API key authentication dependency."""

import hmac
import logging

from fastapi import Header, HTTPException

from app.config import get_settings

logger = logging.getLogger("app.security")

_401 = HTTPException(
    status_code=401,
    detail="Invalid or missing API key.",
    headers={"WWW-Authenticate": "X-API-Key"},
)


async def require_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> None:
    """Raise HTTP 401 if the X-API-Key header is absent or incorrect.

    Uses hmac.compare_digest to prevent timing-based enumeration of the key.
    """
    if x_api_key is None:
        logger.warning("Request rejected: missing X-API-Key header")
        raise _401
    if not hmac.compare_digest(x_api_key, get_settings().api_key):
        logger.warning("Request rejected: invalid X-API-Key")
        raise _401
