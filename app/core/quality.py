"""Pluggable quality-scoring interface for LLM responses."""

from abc import ABC, abstractmethod
from decimal import Decimal

_REFUSAL_PHRASES = ("i cannot", "i can't", "i'm sorry, i can't", "i'm sorry, i cannot")

_LENGTH_FLOOR = 20   # words below this are considered too short
_LENGTH_TARGET = 80  # words at or above this get full length credit


class QualityScorer(ABC):
    """Abstract base for quality scorers."""

    @abstractmethod
    async def score(self, prompt: str, response: str) -> tuple[Decimal, str]:
        """Return (score 0–5, reason string) for a prompt/response pair."""


class HeuristicScorer(QualityScorer):
    """Cheap, deterministic quality heuristic.

    Signals:
    - length: response length in tokens/words (too short = lower)
    - refusal detection: phrase match on "I cannot", "I can't", "I'm sorry"
    - error signal: empty response -> 0
    Score is Decimal between 0 and 5.
    Returns (score, reason).
    """

    async def score(self, prompt: str, response: str) -> tuple[Decimal, str]:
        """Score response quality heuristically."""
        text = response.strip()

        if not text:
            return Decimal("0.00"), "empty response"

        lower = text.lower()
        if any(phrase in lower for phrase in _REFUSAL_PHRASES):
            return Decimal("1.00"), "refusal detected"

        word_count = len(text.split())
        if word_count < _LENGTH_FLOOR:
            length_score = Decimal("2.00") + Decimal(str(word_count / _LENGTH_FLOOR))
        else:
            capped = min(word_count, _LENGTH_TARGET)
            ratio = (capped - _LENGTH_FLOOR) / (_LENGTH_TARGET - _LENGTH_FLOOR)
            length_score = Decimal("3.00") + Decimal(str(ratio)) * Decimal("2.00")

        final = min(length_score, Decimal("5.00")).quantize(Decimal("0.01"))
        return final, f"length={word_count} words"


_SCORERS: dict[str, QualityScorer] = {"heuristic": HeuristicScorer()}


def get_scorer(source: str) -> QualityScorer:
    """Return the scorer registered for *source*.

    Args:
        source: One of the registered scorer keys.

    Returns:
        QualityScorer instance.

    Raises:
        KeyError: If *source* is not registered.
    """
    return _SCORERS[source]
