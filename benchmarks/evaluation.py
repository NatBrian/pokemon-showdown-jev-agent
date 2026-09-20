"""Provider-independent outcome and decision metrics."""

from dataclasses import dataclass, field
from collections.abc import Iterable, Mapping
from typing import Any


@dataclass
class SeriesMetrics:
    battles: int
    wins: int
    losses: int
    draws: int
    decisions: int
    fallbacks: int
    illegal_actions: int
    stale_responses: int
    decision_latencies_ms: list[float] = field(default_factory=list)


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def latency_percentiles(values: Iterable[float]) -> dict[str, float | None]:
    ordered = [float(value) for value in values]
    return {
        "p50": _rounded_percentile(ordered, 0.50),
        "p95": _rounded_percentile(ordered, 0.95),
        "p99": _rounded_percentile(ordered, 0.99),
    }


def _rounded_percentile(values: list[float], fraction: float) -> float | None:
    value = _percentile(values, fraction)
    return round(value, 6) if value is not None else None


def summarize_series(events: Iterable[Mapping[str, Any]]) -> SeriesMetrics:
    battles = wins = losses = draws = 0
    decisions = fallbacks = illegal_actions = stale_responses = 0
    latencies: list[float] = []

    for event in events:
        event_type = event.get("type")
        if event_type == "BATTLE_END":
            battles += 1
            won = event.get("won")
            if won is True:
                wins += 1
            elif won is False:
                losses += 1
            else:
                draws += 1
            continue

        if event_type != "TURN_DECISION":
            continue
        decisions += 1
        if event.get("is_fallback") is True:
            fallbacks += 1
        reason = str(event.get("fallback_reason") or "").lower()
        if event.get("stale_response") is True or "stale" in reason:
            stale_responses += 1

        validation = event.get("validation")
        validation = validation if isinstance(validation, Mapping) else {}
        if (
            event.get("illegal_action") is True
            or validation.get("illegal_action") is True
        ):
            illegal_actions += 1
        latency = validation.get("latency_ms")
        if isinstance(latency, (int, float)) and not isinstance(latency, bool):
            latencies.append(float(latency))

    return SeriesMetrics(
        battles=battles,
        wins=wins,
        losses=losses,
        draws=draws,
        decisions=decisions,
        fallbacks=fallbacks,
        illegal_actions=illegal_actions,
        stale_responses=stale_responses,
        decision_latencies_ms=latencies,
    )
