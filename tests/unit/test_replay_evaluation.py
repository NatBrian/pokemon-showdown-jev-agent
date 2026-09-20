import json

import pytest

from benchmarks.evaluation import SeriesMetrics, latency_percentiles, summarize_series
from benchmarks.replay_decisions import read_decision_packages, write_decision_package


def _decision(turn, *, fallback=False, reason=None, latency=10.0, illegal=False):
    return {
        "type": "TURN_DECISION",
        "turn": turn,
        "state_schema": 2,
        "criteria": {"move_a": "Move A"},
        "fingerprint": {"request_id": f"req-{turn}"},
        "beliefs": {"opponent_slots": []},
        "jev_response": {"probabilities": {"move_a": 1.0}},
        "is_fallback": fallback,
        "fallback_reason": reason,
        "validation": {"latency_ms": latency, "illegal_action": illegal},
        "submitted_order": {"chosen_id": "move_a"},
    }


def test_decision_package_round_trips_json_lines(tmp_path):
    path = tmp_path / "decisions.jsonl"
    event = _decision(4)

    write_decision_package(path, event)
    assert list(read_decision_packages(path)) == [event]


def test_decision_package_rejects_malformed_line_with_line_number(tmp_path):
    path = tmp_path / "decisions.jsonl"
    path.write_text('{"type":"TURN_DECISION"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(ValueError, match=r"line 2"):
        list(read_decision_packages(path))


def test_decision_package_rejects_non_object_json_line(tmp_path):
    path = tmp_path / "decisions.jsonl"
    path.write_text('["not an event"]\n', encoding="utf-8")

    with pytest.raises(ValueError, match=r"line 1"):
        list(read_decision_packages(path))


def test_series_metrics_count_only_recorded_outcomes_and_decisions():
    events = [
        _decision(1, latency=10.0),
        _decision(2, fallback=True, reason="Stale Jev response", latency=20.0),
        _decision(3, fallback=True, reason="provider error", latency=30.0, illegal=True),
        {"type": "BATTLE_END", "won": True},
        {"type": "BATTLE_END", "won": False},
        {"type": "BATTLE_END", "won": None},
    ]

    metrics = summarize_series(events)

    assert isinstance(metrics, SeriesMetrics)
    assert metrics.battles == 3
    assert metrics.wins == 1
    assert metrics.losses == 1
    assert metrics.draws == 1
    assert metrics.decisions == 3
    assert metrics.fallbacks == 2
    assert metrics.illegal_actions == 1
    assert metrics.stale_responses == 1
    assert metrics.decision_latencies_ms == [10.0, 20.0, 30.0]


def test_latency_percentiles_are_deterministic():
    percentiles = latency_percentiles([10.0, 20.0, 30.0, 40.0])

    assert percentiles["p50"] == 25.0
    assert percentiles["p95"] == 38.5
    assert percentiles["p99"] == 39.7
    assert latency_percentiles([]) == {"p50": None, "p95": None, "p99": None}
