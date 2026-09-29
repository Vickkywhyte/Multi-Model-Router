"""Pydantic v2 request/response schemas for the /v1/route endpoint."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    """Incoming prompt to be classified and routed."""

    prompt: str = Field(..., description="The prompt text to send to the LLM.")
    max_tokens: int = Field(1024, description="Maximum tokens to generate.")
    temperature: float = Field(
        0.0, description="Sampling temperature (0 = deterministic)."
    )


class RouteResponse(BaseModel):
    """Full result returned after routing, completion, and cost logging."""

    request_id: str = Field(..., description="UUID4 identifier for this request.")
    model_name: str = Field(..., description="Gemini model that handled the prompt.")
    classifier_label: Literal["simple", "medium", "complex"] = Field(
        ..., description="Complexity tier assigned by the classifier."
    )
    classifier_reason: str = Field(
        ..., description="Human-readable explanation of the classification."
    )
    text: str = Field(..., description="Generated completion text.")
    tokens_in: int = Field(..., description="Number of input tokens consumed.")
    tokens_out: int = Field(..., description="Number of output tokens generated.")
    cost_usd: Decimal = Field(
        ..., description="Estimated cost in USD for this request."
    )
    latency_ms: int = Field(..., description="End-to-end latency in milliseconds.")
