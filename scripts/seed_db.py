"""Seed the 'models' table with Gemini model pricing data.

Idempotent — safe to run multiple times.  Uses ON CONFLICT DO NOTHING so
existing rows are left untouched.

Usage:
    python scripts/seed_db.py
"""

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.model import Model
from app.observability.logger import get_logger, setup_logging

setup_logging()
logger = get_logger("scripts.seed_db")

_MODELS = [
    {
        "name": "gemini-3.5-flash-lite",
        "provider": "google",
        "input_price_per_million": 0.30,
        "output_price_per_million": 2.50,
        "context_window": 1_000_000,
    },
    {
        "name": "gemini-3.5-flash",
        "provider": "google",
        "input_price_per_million": 1.50,
        "output_price_per_million": 9.00,
        "context_window": 1_000_000,
    },
    {
        "name": "gemini-2.5-pro",
        "provider": "google",
        "input_price_per_million": 1.25,
        "output_price_per_million": 10.00,
        "context_window": 2_000_000,
    },
]


async def seed() -> None:
    """Insert Gemini model rows, skipping any that already exist."""
    inserted = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        for data in _MODELS:
            result = await session.execute(
                select(Model).where(Model.name == data["name"])
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                skipped += 1
                continue

            session.add(Model(**data))
            inserted += 1

        await session.commit()

    logger.info(
        "Seeded %d models (%d already existed)",
        inserted,
        skipped,
    )


if __name__ == "__main__":
    asyncio.run(seed())
