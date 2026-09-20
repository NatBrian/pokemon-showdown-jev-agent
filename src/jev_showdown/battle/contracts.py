"""Shared, JSON-safe contracts for the battle decision boundary."""

from dataclasses import asdict, dataclass
import math
from typing import Any, Literal


FactSource = Literal["observed", "calculated", "inferred", "unknown"]
RequestType = Literal["move", "switch", "wait", "team_preview", "unknown"]


@dataclass(frozen=True)
class Fact:
    value: Any
    source: FactSource
    unit: str | None = None
    confidence: float | None = None
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.source not in {"observed", "calculated", "inferred", "unknown"}:
            raise ValueError(f"unknown fact source: {self.source!r}")
        if self.confidence is not None:
            if not isinstance(self.confidence, (int, float)) or not math.isfinite(
                float(self.confidence)
            ):
                raise ValueError("confidence must be a finite number")
            if not 0.0 <= float(self.confidence) <= 1.0:
                raise ValueError("confidence must be between 0.0 and 1.0")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation, including unknown fields."""
        result = asdict(self)
        result["assumptions"] = list(self.assumptions)
        return result


@dataclass(frozen=True)
class BattleRequestMetadata:
    battle_id: str | None
    request_id: str | int | None
    state_version: int
    turn: int
    request_type: RequestType
    force_switch: bool
    wait: bool
    trapped: bool
    maybe_trapped: bool
    deadline_monotonic: float | None


@dataclass(frozen=True)
class DecisionFingerprint:
    battle_id: str | None
    request_id: str | int | None
    state_version: int
    turn: int
    candidate_ids: tuple[str, ...]


def build_decision_fingerprint(
    metadata: BattleRequestMetadata,
    candidate_ids: tuple[str, ...],
) -> DecisionFingerprint:
    return DecisionFingerprint(
        battle_id=metadata.battle_id,
        request_id=metadata.request_id,
        state_version=metadata.state_version,
        turn=metadata.turn,
        candidate_ids=tuple(candidate_ids),
    )
