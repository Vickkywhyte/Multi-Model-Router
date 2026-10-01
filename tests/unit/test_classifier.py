"""Tests for the rule-based complexity classifier."""

import pytest

from app.core.classifier import ClassificationResult, classify

# ---------------------------------------------------------------------------
# Parametrized label tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("prompt,expected_label", [
    ("What is Python?", "simple"),
    ("Who is Alan Turing?", "simple"),
    ("", "simple"),
    ("Define recursion.", "simple"),
])
def test_simple_labels(prompt: str, expected_label: str) -> None:
    result = classify(prompt)
    assert result.label == expected_label, (
        f"Expected {expected_label!r} for {prompt!r}, got {result.label!r} "
        f"(scores={result.scores})"
    )


def test_medium_or_complex_multi_question() -> None:
    prompt = (
        "What are the trade-offs between SQL and NoSQL databases? "
        "When should you choose one over the other? "
        "What are the main consistency models?"
    )
    result = classify(prompt)
    assert result.label in ("medium", "complex"), (
        f"Expected medium or complex, got {result.label!r} (scores={result.scores})"
    )


# ---------------------------------------------------------------------------
# Code fence raises score
# ---------------------------------------------------------------------------

def test_code_fence_raises_score() -> None:
    base = "Explain loops."
    with_fence = "Explain loops.\n```python\nfor i in range(10): pass\n```"
    r_base = classify(base)
    r_fence = classify(with_fence)
    assert sum(r_fence.scores.values()) > sum(r_base.scores.values())


# ---------------------------------------------------------------------------
# Multiple question marks raise score
# ---------------------------------------------------------------------------

def test_multiple_questions_raise_score() -> None:
    single = "What is Python?"
    multi = "What is Python? Why use it? When should you avoid it?"
    r_single = classify(single)
    r_multi = classify(multi)
    assert r_multi.scores["question_marks"] > r_single.scores["question_marks"]


# ---------------------------------------------------------------------------
# Multi-step keywords raise score
# ---------------------------------------------------------------------------

def test_step_by_step_keyword() -> None:
    without = "Explain merge sort."
    with_kw = "Explain merge sort step by step."
    assert sum(classify(with_kw).scores.values()) > sum(classify(without).scores.values())


# ---------------------------------------------------------------------------
# Design + architect → complex
# ---------------------------------------------------------------------------

def test_design_architect_complex() -> None:
    # 40+ words (length=2) + capped multi-step keywords (4) = total 6 → complex
    prompt = (
        "Design a distributed event-driven microservices architecture from scratch. "
        "Architect each individual service carefully and explain why each design choice "
        "was made, step by step, comparing all major alternatives in depth and "
        "evaluating their trade-offs thoroughly. Consider scalability and fault tolerance."
    )
    result = classify(prompt)
    assert result.label == "complex", f"Scores: {result.scores}"


# ---------------------------------------------------------------------------
# Very long prompt → complex
# ---------------------------------------------------------------------------

def test_very_long_prompt_is_complex() -> None:
    prompt = " ".join(["word"] * 200)
    result = classify(prompt)
    assert result.label == "complex", f"Scores: {result.scores}"


# ---------------------------------------------------------------------------
# Bullet list raises score
# ---------------------------------------------------------------------------

def test_bullet_list_raises_score() -> None:
    plain = "Explain these topics: A B C."
    bulleted = "Explain these topics:\n- A\n- B\n- C"
    assert sum(classify(bulleted).scores.values()) > sum(classify(plain).scores.values())


# ---------------------------------------------------------------------------
# Reason is non-empty
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("prompt", [
    "What is Python?",
    "",
    "Design a distributed system step by step with code examples.",
    "Convert 100 USD to EUR.",
])
def test_reason_non_empty(prompt: str) -> None:
    result = classify(prompt)
    assert result.reason, f"Reason should not be empty for prompt: {prompt!r}"


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

def test_returns_classification_result_instance() -> None:
    result = classify("What is Python?")
    assert isinstance(result, ClassificationResult)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_determinism() -> None:
    prompt = "Analyze and compare sorting algorithms step by step."
    r1 = classify(prompt)
    r2 = classify(prompt)
    assert r1.label == r2.label
    assert r1.reason == r2.reason
    assert r1.scores == r2.scores


# ---------------------------------------------------------------------------
# Threshold calibration tests
# ---------------------------------------------------------------------------

def test_short_hello_is_simple() -> None:
    result = classify("Hello")
    assert result.label == "simple", f"Scores: {result.scores}"


def test_compare_keyword_is_medium() -> None:
    result = classify("Compare Python and Rust for building a web backend")
    assert result.label == "medium", f"Scores: {result.scores}"


def test_long_multi_signal_prompt_is_complex() -> None:
    prompt = (
        "Step by step, design a distributed event-driven architecture with retries "
        "and idempotency. Compare message queues vs event streams. Analyze failure "
        "modes. Provide code examples in Python and Go."
    )
    result = classify(prompt)
    assert result.label == "complex", f"Scores: {result.scores}"
