"""FastAPI application entrypoint for the Multi-Model Router.

Wires together configuration, logging, middleware, and API routers.
The lifespan context manager handles startup and shutdown logging.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import get_settings
from app.observability.logger import get_logger, setup_logging
from app.observability.tracing import RequestTracingMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    setup_logging(settings.log_level)
    logger = get_logger("app.main")
    logger.info(
        "Application starting",
        extra={"app_name": settings.app_name, "env": settings.app_env},
    )
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

if settings.app_env == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(RequestTracingMiddleware)

app.include_router(v1_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "healthy", "environment": settings.app_env, "version": "0.1.0"}
