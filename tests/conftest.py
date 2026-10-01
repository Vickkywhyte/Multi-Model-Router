"""Root test configuration and shared fixtures."""

import os

import pytest

_TEST_API_KEY = "test-api-key"

# Set required env vars before any app module is imported at collection time.
os.environ.setdefault("GEMINI_API_KEY", "test-placeholder")
os.environ.setdefault("API_KEY", _TEST_API_KEY)


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-placeholder")
    monkeypatch.setenv("API_KEY", _TEST_API_KEY)
    from app.config import get_settings
    get_settings.cache_clear()
