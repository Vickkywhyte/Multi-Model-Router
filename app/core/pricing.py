"""Tier-to-model mapping. Single source of truth for routing decisions."""

from typing import Literal

TIER_TO_MODEL: dict[str, str] = {
    "simple": "gemini-3.5-flash-lite",
    "medium": "gemini-3.5-flash",
    "complex": "gemini-2.5-pro",
}

MODEL_TO_TIER: dict[str, str] = {v: k for k, v in TIER_TO_MODEL.items()}


def tier_to_model(label: Literal["simple", "medium", "complex"]) -> str:
    """Return the model name for a complexity label.

    Args:
        label: One of "simple", "medium", or "complex".

    Returns:
        The Gemini model identifier string.

    Raises:
        ValueError: If the label is not recognised.
    """
    try:
        return TIER_TO_MODEL[label]
    except KeyError as exc:
        raise ValueError(f"Unknown complexity label: {label!r}") from exc
