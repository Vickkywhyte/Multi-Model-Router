"""Structured JSON logging setup using python-json-logger.

Call setup_logging() once at application startup, then obtain loggers
with logging.getLogger(name) directly.
"""

import logging

from pythonjsonlogger import json


def setup_logging(log_level: str = "INFO") -> None:
    """Configure the root logger with a JSON formatter.

    Idempotent — safe to call multiple times; only the first call takes effect.

    Args:
        log_level: The logging level string (e.g. "INFO", "DEBUG").
    """
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler()
    formatter = json.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(log_level.upper())
