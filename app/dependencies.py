"""Shared FastAPI dependency re-exports.

Route handlers import get_db and get_settings from here so that the
rest of the codebase has a single import path for common dependencies.
"""

from app.config import get_settings
from app.db.session import get_db

__all__ = ["get_db", "get_settings"]
