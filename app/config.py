"""Application configuration loaded from environment variables and .env file.

All settings are read via pydantic-settings. Never call os.getenv() elsewhere
in the codebase — import get_settings() instead.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "multi-model-router"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/v1"

    # Real deployments must set GEMINI_API_KEY in .env; tests mock the provider
    # so this value is never forwarded to the Gemini API in CI.
    gemini_api_key: str = "test-placeholder-key-not-used"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/router"
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()
