"""Request tracing middleware that attaches a unique ID to every HTTP request.

Logs request start and finish (including duration) as structured JSON events,
and echoes the request ID back to the caller via the X-Request-ID header.
"""

import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.observability.logger import get_logger

_logger = get_logger("app.tracing")


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware that generates a request_id, logs start/finish, sets X-Request-ID."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request, logging timing and attaching the request ID.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            The HTTP response with X-Request-ID header added.
        """
        request_id = str(uuid4())
        start = time.perf_counter()

        _logger.info(
            "request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )

        try:
            response: Response = await call_next(request)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            status_code = getattr(response, "status_code", None)
            _logger.info(
                "request finished",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )

        response.headers["X-Request-ID"] = request_id
        return response
