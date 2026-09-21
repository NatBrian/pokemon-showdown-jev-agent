from dataclasses import dataclass, field
import math
from collections.abc import Mapping
from typing import Any


PROBABILITY_SUM_TOLERANCE = 0.01
PROBABILITY_SUM_NUMERIC_EPSILON = 1e-12

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


class JevChoiceValidationError(ValueError):
    """The provider returned a Choice that cannot safely be submitted."""


def validate_jev_choice(
    response: Mapping[str, Any], criteria: Mapping[str, str]
) -> tuple[str, float, dict[str, float]]:
    """Validate the typed Choice contract against the current action IDs."""
    answers = response.get("answers")
    action = answers.get("action") if isinstance(answers, Mapping) else None
    if not isinstance(action, Mapping):
        raise JevChoiceValidationError("answers.action must be an object")
    if action.get("type") != "choice":
        raise JevChoiceValidationError("answers.action.type must be 'choice'")

    choice = action.get("choice")
    if not isinstance(choice, str) or not choice:
        raise JevChoiceValidationError("answers.action.choice is required")
    if choice not in criteria:
        raise JevChoiceValidationError("choice is not present in criteria")

    confidence = action.get("confidence", 0.0)
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise JevChoiceValidationError("confidence must be numeric")
    if not math.isfinite(float(confidence)) or not 0.0 <= float(confidence) <= 1.0:
        raise JevChoiceValidationError("confidence is out of range")

    raw_probabilities = action.get("probabilities", {})
    if raw_probabilities is None:
        raise JevChoiceValidationError("probabilities must be an object")
    if not isinstance(raw_probabilities, Mapping):
        raise JevChoiceValidationError("probabilities must be an object")

    probabilities: dict[str, float] = {}
    for key, value in raw_probabilities.items():
        if not isinstance(key, str):
            raise JevChoiceValidationError("probability keys must be strings")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise JevChoiceValidationError(f"probability for {key!r} must be numeric")
        numeric = float(value)
        if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
            raise JevChoiceValidationError(f"probability for {key!r} is out of range")
        probabilities[key] = numeric

    if probabilities:
        missing = sorted(set(criteria) - set(probabilities))
        if missing:
            raise JevChoiceValidationError(
                "probability map is missing criteria IDs: " + ", ".join(missing)
            )
        extra = sorted(set(probabilities) - set(criteria))
        if extra:
            raise JevChoiceValidationError(
                "probability map contains unknown criteria IDs: " + ", ".join(extra)
            )
        total = sum(probabilities.values())
        if total <= 0.0:
            raise JevChoiceValidationError("probability sum must be positive")
        # Jev can round a valid probability vector to two decimals, as in the
        # observed 0.99 total. Keep the tolerance narrow and normalize only
        # that small rounding discrepancy.
        if abs(total - 1.0) > (
            PROBABILITY_SUM_TOLERANCE + PROBABILITY_SUM_NUMERIC_EPSILON
        ):
            raise JevChoiceValidationError("probability sum must equal 1.0")
        probabilities = {
            key: value / total for key, value in probabilities.items()
        }

    return choice, float(confidence), probabilities
