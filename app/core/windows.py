"""Canonical window label ↔ hour-count mapping for metrics queries."""

from typing import Final

WINDOW_HOURS: Final[dict[str, int]] = {
    "1h": 1,
    "24h": 24,
    "7d": 168,
    "30d": 720,
}


def hours_to_label(hours: int) -> str:
    for label, h in WINDOW_HOURS.items():
        if h == hours:
            return label
    return f"{hours}h"
