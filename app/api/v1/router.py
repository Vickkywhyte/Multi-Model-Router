"""API v1 router — aggregates all v1 endpoint modules."""

from fastapi import APIRouter

from app.api.v1 import feedback as feedback_module
from app.api.v1 import metrics as metrics_module
from app.api.v1 import route as route_module

router = APIRouter()

router.include_router(route_module.router)
router.include_router(metrics_module.router)
router.include_router(feedback_module.router)


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Health-check ping endpoint."""
    return {"message": "pong"}
