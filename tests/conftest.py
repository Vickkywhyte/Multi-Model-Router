"""Root test configuration and shared fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-placeholder")
    from app.config import get_settings
    get_settings.cache_clear()
