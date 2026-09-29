#!/usr/bin/env python3
"""Benchmark the same prompt across all three Gemini models.

Usage:
    python scripts/benchmark.py
    python scripts/benchmark.py "Explain quantum entanglement"

Calls each provider directly (no HTTP endpoint) and prints a markdown
comparison table plus the classifier's decision for the same prompt.
"""

import asyncio

# Ensure the project root is on sys.path when run as a script.
import os
import sys
import time
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.classifier import classify
from app.observability.logger import get_logger, setup_logging
from app.providers.base import CompletionRequest
from app.providers.gemini_provider import GeminiProvider

setup_logging("INFO")
logger = get_logger("benchmark")

_DEFAULT_PROMPT = "What is the capital of France?"

_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-pro",
]


async def _run_one(
    provider: GeminiProvider,
    model_name: str,
    prompt: str,
) -> dict[str, object]:
    request = CompletionRequest(prompt=prompt, model_name=model_name)
    start = time.monotonic()
    try:
        result = await provider.complete(request)
        latency_ms = int((time.monotonic() - start) * 1000)
        cost_usd: Decimal = provider.calculate_cost(
            model_name, result.tokens_in, result.tokens_out
        )
        preview = result.text[:80].replace("\n", " ")
        return {
            "model": model_name,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "preview": preview,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning("Model error", extra={"model": model_name, "error": str(exc)})
        return {
            "model": model_name,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": Decimal("0"),
            "latency_ms": latency_ms,
            "preview": "",
            "error": str(exc),
        }


async def run_benchmark(prompt: str) -> None:
    classification = classify(prompt)
    print(f"\n**Prompt:** {prompt!r}")
    print(f"**Classifier decision:** {classification.label} ({classification.reason})\n")

    provider = GeminiProvider()
    results = []
    for model in _MODELS:
        logger.info("Benchmarking model", extra={"model": model})
        row = await _run_one(provider, model, prompt)
        results.append(row)

    # Print markdown table
    header = "| Model | Tokens In | Tokens Out | Cost (USD) | Latency (ms) | Response Preview |"
    sep    = "|-------|-----------|------------|------------|--------------|------------------|"
    print(header)
    print(sep)
    for r in results:
        preview_col = f"ERROR: {r['error'][:60]}" if r["error"] else r["preview"]
        cost_str = f"{r['cost_usd']:.6f}"
        print(
            f"| {r['model']:<30} | {r['tokens_in']:>9} | {r['tokens_out']:>10} "
            f"| {cost_str:>10} | {r['latency_ms']:>12} | {preview_col} |"
        )
    print()


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip() or _DEFAULT_PROMPT
    asyncio.run(run_benchmark(prompt))


if __name__ == "__main__":
    main()
