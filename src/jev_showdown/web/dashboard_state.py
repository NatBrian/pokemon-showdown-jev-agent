"""Truthful, redacted projection of live battle telemetry for the dashboard."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from statistics import quantiles
from typing import Any, Mapping

from jev_showdown.telemetry.serialization import json_safe


_REDACTED = "[REDACTED]"
_SENSITIVE_KEY = re.compile(
    r"(?:authorization|api[_-]?key|access[_-]?token|auth[_-]?token|password|secret|cookie|credential)",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_dashboard_value(value: Any, *, _key: str | None = None) -> Any:
    """Return JSON-safe telemetry with credential-like fields removed."""
    if _key and _SENSITIVE_KEY.search(_key):
        return _REDACTED
    value = json_safe(value)
    if isinstance(value, Mapping):
        return {
            str(key): redact_dashboard_value(item, _key=str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_dashboard_value(item) for item in value]
    return value


def _copy(value: Any) -> Any:
    return deepcopy(redact_dashboard_value(value))


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _numeric(value: Any) -> float | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _probability_status(response: Mapping[str, Any]) -> tuple[str, dict[str, float] | None]:
    probabilities = response.get("probabilities")
    error = str(response.get("error") or "")
    raw_response = _as_mapping(response.get("raw_response"))
    raw_answers = _as_mapping(raw_response.get("answers"))
    raw_action = _as_mapping(raw_answers.get("action"))
    rejected_map = raw_action.get("probabilities")

    if "probability" in error.lower() and isinstance(rejected_map, Mapping):
        return "rejected", None
    if not isinstance(probabilities, Mapping) or not probabilities:
        return "not_returned", None

    normalized: dict[str, float] = {}
    for key, value in probabilities.items():
        number = _numeric(value)
        if number is None or number < 0:
            return "rejected", None
        normalized[str(key)] = float(number)
    total = sum(normalized.values())
    if abs(total - 1.0) > 1e-6:
        return "rejected", None
    return "valid", normalized


def _unknown_paths(value: Any, path: str = "snapshot") -> list[str]:
    """Collect source-backed unknowns without converting them into guesses."""
    found: list[str] = []
    if isinstance(value, Mapping):
        source = value.get("source")
        if source == "unknown":
            found.append(path)
        for key, item in value.items():
            child = f"{path}.{key}"
            if item is None and key in {
                "species", "item", "ability", "tera_type", "damage", "ko",
                "entry_hazard_damage", "opponent_coverage",
            }:
                found.append(child)
            elif isinstance(item, (Mapping, list)):
                found.extend(_unknown_paths(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_unknown_paths(item, f"{path}[{index}]"))
    return found


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    if percentile == 0.5 and len(ordered) >= 2:
        return quantiles(ordered, n=2, method="inclusive")[0]
    if percentile == 0.95:
        rank = (len(ordered) - 1) * 0.95
    else:
        rank = (len(ordered) - 1) * 0.99
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


class DashboardProjector:
    """Project raw telemetry into a stable, browser-safe dashboard snapshot."""

    def __init__(self) -> None:
        self._run: dict[str, Any] = {
            "status": "READY",
            "format": None,
            "model": None,
            "endpoint_metadata": None,
            "started_at": None,
            "finished_at": None,
            "evaluation_status": None,
            "integrity": {
                "event_records_complete": None,
                "request_response_records_complete": None,
                "credential_leaks": None,
            },
        }
        self._battle: dict[str, Any] = {
            "battle_tag": None,
            "battle_id": None,
            "state": "idle",
            "winner": None,
            "won": None,
            "total_turns": None,
            "replay": "unknown",
        }
        self._renderer: dict[str, Any] = {
            "state": "idle",
            "connection_label": "Waiting for battle",
            "last_observed_at": None,
        }
        self._current_turn: dict[str, Any] | None = None
        self._history: list[dict[str, Any]] = []
        self._inspection: dict[str, Any] | None = None
        self._latencies: list[float] = []
        self._metrics: dict[str, Any] = {
            "battles_completed": 0,
            "jev_calls": 0,
            "valid_choices": 0,
            "fallbacks": 0,
            "illegal_actions": 0,
            "stale_responses": 0,
            "provider_errors": 0,
            "provider_503_errors": 0,
            "request_timeouts": 0,
            "protocol_validation_errors": 0,
            "timer_failures": 0,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
            "latency_p99_ms": None,
        }

    def apply_event(self, event: Mapping[str, Any]) -> None:
        """Apply one already JSON-safe telemetry message."""
        record = _copy(event)
        event_type = record.get("type")
        now = _now()

        if event_type == "EVALUATION_SETUP":
            self._run.update(
                {
                    "format": record.get("battle_format") or record.get("format"),
                    "model": record.get("jev_model") or record.get("model"),
                    "started_at": record.get("started_at") or record.get("run_started_at"),
                    "evaluation_status": record.get("status") or record.get("evaluation_status"),
                }
            )
            self._run["integrity"].update(_as_mapping(record.get("integrity")))
            return

        if event_type == "STATUS_UPDATE":
            self._run["status"] = record.get("status") or self._run["status"]
            if record.get("error"):
                self._renderer.update({"state": "error", "connection_label": record.get("status")})
            elif record.get("busy") is False:
                self._renderer.update({"state": "ready", "connection_label": record.get("status")})
            else:
                self._renderer.update({"state": "connecting", "connection_label": record.get("status")})
            self._renderer["last_observed_at"] = now
            return

        if event_type == "BATTLE_START":
            battle_tag = record.get("battle_tag")
            self._battle = {
                "battle_tag": battle_tag,
                "battle_id": battle_tag,
                "state": "active",
                "winner": None,
                "won": None,
                "total_turns": None,
                "replay": "unknown",
            }
            self._run["format"] = record.get("battle_format") or self._run["format"]
            self._history.clear()
            self._current_turn = None
            self._inspection = None
            self._renderer.update({
                "state": "active",
                "connection_label": "Live Showdown battle",
                "last_observed_at": now,
            })
            return

        if event_type == "BATTLE_FRAME":
            if record.get("battle_tag") == self._battle.get("battle_tag"):
                self._renderer["last_observed_at"] = now
                self._renderer["state"] = "active"
            return

        if event_type == "TURN_DECISION":
            turn = self._build_turn(record)
            self._current_turn = turn
            self._history = [item for item in self._history if not (
                item.get("battle_tag") == turn.get("battle_tag")
                and item.get("turn") == turn.get("turn")
            )]
            self._history.append(turn)
            self._metrics["jev_calls"] += 1
            response = _as_mapping(record.get("jev_response") or record.get("jev"))
            error = str(response.get("error") or "")
            if turn["adapter"]["fallback"].get("is_fallback"):
                self._metrics["fallbacks"] += 1
            elif turn["jev"]["probability_status"] == "valid":
                self._metrics["valid_choices"] += 1
            if error:
                if "probability" in error.lower() or "invalid jev choice" in error.lower():
                    self._metrics["protocol_validation_errors"] += 1
                else:
                    self._metrics["provider_errors"] += 1
                    if "503" in error:
                        self._metrics["provider_503_errors"] += 1
                    if "timeout" in error.lower():
                        self._metrics["request_timeouts"] += 1
            if record.get("stale") or record.get("is_stale"):
                self._metrics["stale_responses"] += 1
            if record.get("illegal_action"):
                self._metrics["illegal_actions"] += 1
            latency = _numeric(response.get("latency_ms"))
            if latency is not None:
                self._latencies.append(float(latency))
                self._metrics["latency_p50_ms"] = _percentile(self._latencies, 0.5)
                self._metrics["latency_p95_ms"] = _percentile(self._latencies, 0.95)
                self._metrics["latency_p99_ms"] = _percentile(self._latencies, 0.99)
            return

        if event_type == "BATTLE_END":
            if record.get("battle_tag") != self._battle.get("battle_tag"):
                return
            self._battle.update({
                "state": "complete",
                "winner": record.get("winner"),
                "won": record.get("won"),
                "total_turns": record.get("total_turns"),
            })
            self._metrics["battles_completed"] = max(
                int(self._metrics["battles_completed"]),
                int(record.get("n_finished") or 0),
            )
            self._run["finished_at"] = record.get("finished_at") or now
            self._renderer.update({
                "state": "complete",
                "connection_label": "Result observed",
                "last_observed_at": now,
            })
            return

        if event_type == "TELEMETRY_ERROR":
            self._run["status"] = "TELEMETRY ERROR"
            self._renderer.update({"state": "error", "connection_label": "Telemetry error"})

    def _build_turn(self, record: Mapping[str, Any]) -> dict[str, Any]:
        snapshot = _as_mapping(record.get("snapshot"))
        request = _as_mapping(record.get("request") or snapshot.get("request"))
        response = _as_mapping(record.get("jev_response") or record.get("jev"))
        validation = _as_mapping(record.get("validation"))
        submitted = _as_mapping(record.get("submitted_order"))
        legal_actions = snapshot.get("legal_actions")
        if not isinstance(legal_actions, list):
            legal_actions = []
        criteria = _as_mapping(record.get("criteria") or snapshot.get("criteria"))
        unknowns = _unknown_paths(snapshot)
        probability_status, probabilities = _probability_status(response)
        is_fallback = bool(record.get("is_fallback") or validation.get("is_fallback"))
        fallback_reason = record.get("fallback_reason") or validation.get("fallback_reason")
        response_error = response.get("error")
        valid_response = not response_error and not is_fallback

        calculated_facts = []
        for action in legal_actions:
            action_map = _as_mapping(action)
            facts = _as_mapping(action_map.get("facts"))
            if facts:
                calculated_facts.append({
                    "candidate_id": action_map.get("id"),
                    "label": action_map.get("label"),
                    "facts": _copy(facts),
                    "source": "harness",
                })

        response_summary = {
            "choice": response.get("choice") if valid_response else None,
            "confidence": _numeric(response.get("confidence")) if valid_response else None,
            "probabilities": probabilities,
            "model": response.get("model"),
            "input_tokens": response.get("input_tokens") if valid_response else None,
            "output_tokens": response.get("output_tokens") if valid_response else None,
            "cost": response.get("cost") if valid_response else None,
            "latency_ms": _numeric(response.get("latency_ms")),
            "error": response_error,
        }
        lifecycle = "FALLBACK USED" if is_fallback else "ORDER SUBMITTED" if submitted.get("message") else "JEV EVALUATING"
        return {
            "battle_tag": record.get("battle_tag") or request.get("battle_id"),
            "turn": record.get("turn") or request.get("turn"),
            "lifecycle_state": lifecycle,
            "showdown": {
                "request": _copy(request),
                "observed_result": None,
                "protocol_evidence": {"raw_frame_captured": False},
            },
            "harness": {
                "snapshot": _copy(snapshot),
                "request_metadata": _copy(request),
                "calculated_facts": calculated_facts,
                "legal_actions": _copy(legal_actions),
                "unknowns": unknowns,
                "handoff_summary": {
                    "candidate_count": len(legal_actions),
                    "criteria_count": len(criteria),
                    "question_count": 1 if record.get("question") or record.get("jev_request") else 0,
                    "state_schema": snapshot.get("state_schema") or record.get("state_schema"),
                    "rqid": request.get("rqid"),
                    "state_version": request.get("state_version"),
                    "request_type": request.get("request_type"),
                    "can_tera": snapshot.get("can_tera"),
                    "unknown_count": len(unknowns),
                },
            },
            "jev": {
                "request_summary": {
                    "model": _as_mapping(record.get("jev_request")).get("model"),
                    "question": _copy(record.get("question") or _as_mapping(record.get("jev_request")).get("questions")),
                    "candidate_count": len(legal_actions),
                },
                "response_summary": response_summary,
                "probability_status": probability_status,
                "raw_response": _copy(response.get("raw_response")),
            },
            "adapter": {
                "validation": _copy(validation),
                "submitted_order": _copy(submitted),
                "fallback": {"is_fallback": is_fallback, "reason": fallback_reason},
            },
            "timing": {
                "response_latency_ms": _numeric(response.get("latency_ms")),
                "wrapper_latency_ms": _numeric(record.get("wrapper_latency_ms")),
                "decision_latency_ms": _numeric(validation.get("latency_ms")),
            },
            "raw_event": _copy(record),
        }

    def select_decision(
        self, battle_tag: str, turn: int, call_id: int | None = None
    ) -> dict[str, Any] | None:
        for item in self._history:
            if item.get("battle_tag") == battle_tag and item.get("turn") == turn:
                if call_id is None or item.get("raw_event", {}).get("call_id") == call_id:
                    self._inspection = {
                        "selected_battle_tag": battle_tag,
                        "selected_turn": turn,
                        "selected_call_id": call_id,
                    }
                    return _copy(item)
        return None

    def snapshot(self) -> dict[str, Any]:
        return _copy({
            "schema_version": 1,
            "kind": "snapshot",
            "emitted_at": _now(),
            "run": self._run,
            "battle": self._battle,
            "renderer": self._renderer,
            "current_turn": self._current_turn,
            "history": self._history,
            "metrics": self._metrics,
            "inspection": self._inspection,
        })
