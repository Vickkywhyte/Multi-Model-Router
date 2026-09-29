"""Redis-backed fixed-window rate limiter."""

import logging

import redis.asyncio as aioredis

logger = logging.getLogger("app.core.rate_limit")


async def check_rate_limit(
    redis_client: aioredis.Redis,
    key: str,
    limit: int,
    window_seconds: int = 60,
) -> tuple[bool, int]:
    """Increment the request counter for *key* and check against *limit*.

    Uses a fixed-window counter: INCR the key; on the first increment set
    an EXPIRE so the window resets automatically.

    Fails open — if Redis raises any exception the request is allowed and
    a warning is logged, so a Redis outage never blocks all traffic.

    Args:
        redis_client: An active redis.asyncio.Redis instance.
        key: The rate-limit bucket key (e.g. ``ratelimit:route:<ip>``).
        limit: Maximum allowed requests within the window.
        window_seconds: Length of the fixed window in seconds.

    Returns:
        ``(allowed, value)`` where *value* is the current counter when
        allowed, or *window_seconds* (suitable for Retry-After) when blocked.
    """
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window_seconds)
        if count <= limit:
            return True, count
        return False, window_seconds
    except Exception as exc:
        logger.warning(
            "Rate-limit Redis error — failing open",
            extra={"key": key, "error": str(exc)},
        )
        return True, 0
