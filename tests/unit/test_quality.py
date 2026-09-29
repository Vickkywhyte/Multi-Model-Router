"""Unit tests for app/core/quality.py — HeuristicScorer."""

from decimal import Decimal

import pytest

from app.core.quality import HeuristicScorer, get_scorer


@pytest.mark.asyncio
async def test_empty_response_scores_zero():
    scorer = HeuristicScorer()
    score, reason = await scorer.score("anything", "")
    assert score == Decimal("0.00")
    assert "empty" in reason


@pytest.mark.asyncio
async def test_refusal_phrase_scores_low():
    scorer = HeuristicScorer()
    score, reason = await scorer.score("a question", "I cannot answer that.")
    assert score <= Decimal("2.00")
    assert "refusal" in reason


@pytest.mark.asyncio
async def test_normal_response_scores_at_least_three():
    scorer = HeuristicScorer()
    normal = (
        "The capital of France is Paris. It has been the political, cultural, and "
        "commercial centre of France since the 10th century. Paris is renowned for "
        "its art, fashion, gastronomy and culture."
    )
    score, reason = await scorer.score("What is the capital of France?", normal)
    assert score >= Decimal("3.00")


@pytest.mark.asyncio
async def test_returns_decimal_and_str_tuple():
    scorer = HeuristicScorer()
    result = await scorer.score("prompt", "Some response text here.")
    assert isinstance(result, tuple)
    assert len(result) == 2
    score, reason = result
    assert isinstance(score, Decimal)
    assert isinstance(reason, str)


@pytest.mark.asyncio
async def test_score_bounded_between_zero_and_five():
    scorer = HeuristicScorer()
    very_long = " ".join(["word"] * 500)
    score, _ = await scorer.score("prompt", very_long)
    assert Decimal("0.00") <= score <= Decimal("5.00")


def test_get_scorer_returns_heuristic_scorer():
    scorer = get_scorer("heuristic")
    assert isinstance(scorer, HeuristicScorer)


def test_get_scorer_unknown_raises_key_error():
    with pytest.raises(KeyError):
        get_scorer("nonexistent_scorer")
