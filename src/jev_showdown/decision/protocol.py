from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class JevDecisionResponse:
    model: str
    choice: str | None
    confidence: float
    probabilities: dict[str, float] = field(default_factory=dict)
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: str = "0"
    raw_response: dict[str, Any] = field(default_factory=dict)
    request_payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
