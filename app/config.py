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

    # Required — must be set via GEMINI_API_KEY in .env or the environment.
    # The app raises a ValidationError at startup if this is missing, which is
    # intentional: fail fast rather than starting and breaking on the first request.
    gemini_api_key: str

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/router"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_per_minute: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
