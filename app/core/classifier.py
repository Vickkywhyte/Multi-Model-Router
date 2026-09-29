"""Rule-based prompt complexity classifier. No LLM calls, no network, no DB."""

import hashlib
from typing import Literal

from pydantic import BaseModel

from app.observability.logger import get_logger

logger = get_logger("app.core.classifier")

_MULTI_STEP_KEYWORDS = [
    "step by step", "and then", "after that", "compare", "analyze",
    "explain why", "design", "architect", "refactor", "prove",
    "evaluate", "critique", "in depth",
]

_SIMPLE_KEYWORDS = [
    "what is", "define", "who is", "when is", "translate", "convert",
    "list", "name", "give me an example",
]


class ClassificationResult(BaseModel):
    label: Literal["simple", "medium", "complex"]
    reason: str
    scores: dict[str, int]


def classify(prompt: str) -> ClassificationResult:
    """Classify prompt complexity without any external calls.

    Args:
        prompt: The raw prompt string to classify.

    Returns:
        ClassificationResult with label, reason, and per-signal scores.
    """
    prompt_lower = prompt.lower()
    words = prompt.split()
    word_count = len(words)

    scores: dict[str, int] = {}

    # Length contribution
    length_score = word_count // 20
    scores["length"] = length_score

    # Code fences
    fence_score = 3 if "```" in prompt else 0
    scores["code_fences"] = fence_score

    # Question marks (capped at 3)
    qmark_score = min(prompt.count("?"), 3)
    scores["question_marks"] = qmark_score

    # Bullet / numbered list lines (capped at 3)
    list_score = 0
    for line in prompt.splitlines():
        stripped = line.strip()
        if stripped and (
            stripped[0] in ("-", "*")
            or (len(stripped) >= 2 and stripped[0].isdigit() and stripped[1] == ".")
        ):
            list_score += 1
    scores["list_items"] = min(list_score, 3)

    # Multi-step keywords (capped at 4)
    multi_hits = sum(1 for kw in _MULTI_STEP_KEYWORDS if kw in prompt_lower)
    scores["multi_step_keywords"] = min(multi_hits, 4)

    # Simple-task keywords (floored at -2)
    simple_hits = sum(1 for kw in _SIMPLE_KEYWORDS if kw in prompt_lower)
    scores["simple_keywords"] = max(-simple_hits, -2)

    # Single short question penalty
    short_single_q = -1 if (prompt.count("?") == 1 and word_count < 15) else 0
    scores["short_single_question"] = short_single_q

    total = sum(scores.values())

    if total <= 1:
        label: Literal["simple", "medium", "complex"] = "simple"
    elif total <= 5:
        label = "medium"
    else:
        label = "complex"

    reason = _build_reason(word_count, scores, total)

    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    logger.debug(
        "Classified prompt",
        extra={"prompt_hash": prompt_hash, "label": label, "total_score": total},
    )

    return ClassificationResult(label=label, reason=reason, scores=scores)


def _build_reason(word_count: int, scores: dict[str, int], total: int) -> str:
    if word_count == 0:
        return "Empty prompt"

    parts: list[str] = []

    if word_count < 15 and scores.get("short_single_question", 0) < 0:
        parts.append(f"Short factual question ({word_count} words)")
    elif word_count >= 20:
        parts.append(f"Long prompt ({word_count} words)")
    else:
        parts.append(f"Prompt ({word_count} words)")

    if scores.get("code_fences", 0) > 0:
        parts.append("code fences")

    if scores.get("question_marks", 0) > 0:
        parts.append(f"{scores['question_marks']} question(s)")

    if scores.get("list_items", 0) > 0:
        parts.append(f"{scores['list_items']} list item(s)")

    if scores.get("multi_step_keywords", 0) > 0:
        parts.append(f"{scores['multi_step_keywords']} multi-step keyword(s)")

    if scores.get("simple_keywords", 0) < 0:
        parts.append("simple-task keywords")

    if len(parts) > 1:
        return " with ".join(parts[:1] + [", ".join(parts[1:])]).rstrip(" with")
    return parts[0]
