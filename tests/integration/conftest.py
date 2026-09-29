"""Integration test configuration and shared fixtures."""

import uuid
from collections.abc import Generator
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import feedback as feedback_module
from app.api.v1 import metrics as metrics_module
from app.api.v1 import route as route_module
from app.api.v1.route import get_provider_dep
from app.dependencies import get_db
from app.providers.base import CompletionResult


@pytest.fixture
def mock_session():
    def _factory(model_id: uuid.UUID | None = None) -> MagicMock:
        session = MagicMock(spec=AsyncSession)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        scalar = MagicMock()
        if model_id is not None:
            row = MagicMock()
            row.id = model_id
            scalar.scalar_one_or_none = MagicMock(return_value=row)
        else:
            scalar.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=scalar)
        return session

    return _factory


@pytest.fixture
def mock_provider():
    def _factory(
        text: str = "Hello!",
        tokens_in: int = 10,
        tokens_out: int = 5,
        model_name: str = "gemini-3.5-flash-lite",
        cost: Decimal = Decimal("0.000001"),
        raise_exc: Exception | None = None,
    ) -> MagicMock:
        provider = MagicMock()
        if raise_exc is not None:
            provider.complete = AsyncMock(side_effect=raise_exc)
        else:
            provider.complete = AsyncMock(
                return_value=CompletionResult(
                    text=text,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    model_name=model_name,
                )
            )
        provider.calculate_cost = MagicMock(return_value=cost)
        return provider

    return _factory


@pytest.fixture
def client_factory():
    @contextmanager
    def _factory(
        session: MagicMock,
        provider: MagicMock | None = None,
    ) -> Generator[TestClient, None, None]:
        app = FastAPI()
        app.include_router(route_module.router, prefix="/v1")
        app.include_router(metrics_module.router, prefix="/v1")
        app.include_router(feedback_module.router, prefix="/v1")

        async def override_get_db() -> AsyncSession:
            yield session

        app.dependency_overrides[get_db] = override_get_db

        if provider is not None:
            def override_get_provider_dep() -> MagicMock:
                return provider

            app.dependency_overrides[get_provider_dep] = override_get_provider_dep

        with TestClient(app) as client:
            yield client

    return _factory
