"""Shared FastAPI dependency re-exports.

Route handlers import get_db and get_settings from here so that the
rest of the codebase has a single import path for common dependencies.
"""

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.config import get_settings
from app.db.session import get_db


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Yield a redis.asyncio.Redis client, closing it on teardown."""
    client: aioredis.Redis = aioredis.from_url(
        get_settings().redis_url, decode_responses=True
    )
    try:
        yield client
    finally:
        await client.aclose()


__all__ = ["get_db", "get_redis", "get_settings"]
