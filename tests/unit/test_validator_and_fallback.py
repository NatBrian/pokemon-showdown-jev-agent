# tests/unit/test_validator_and_fallback.py
from unittest.mock import MagicMock
from poke_env.battle import AbstractBattle
from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.battle.contracts import BattleRequestMetadata, build_decision_fingerprint
from jev_showdown.decision.protocol import JevDecisionResponse
from jev_showdown.strategy.fallback import resolve_order, select_deterministic_fallback


def _fact(value, source="calculated", unit="boolean"):
    return {"value": value, "source": source, "unit": unit}

def test_resolve_order_valid_choice():
    mock_order = MagicMock()
    candidates = {
        "move_earthquake": CandidateAction("move_earthquake", "move", "Earthquake", mock_order, {})
    }
    jev_res = JevDecisionResponse(
        model="jev-1.13-free",
        choice="move_earthquake",
        confidence=0.9
    )
    result = resolve_order(jev_res, candidates, MagicMock())
    assert not result.is_fallback
    assert result.fallback_reason is None
    assert result.order == mock_order
    assert result.chosen_id == "move_earthquake"

def test_resolve_order_fallback_on_error():
    mock_order1 = MagicMock()
    mock_order2 = MagicMock()
    candidates = {
        "move_tackle": CandidateAction("move_tackle", "move", "Tackle", mock_order1, {"base_power": 40}),
        "move_earthquake": CandidateAction("move_earthquake", "move", "Earthquake", mock_order2, {"base_power": 100})
    }
    jev_res = JevDecisionResponse(
        model="jev-1.13-free",
        choice=None,
        confidence=0.0,
        error="Timeout exceeded"
    )
    result = resolve_order(jev_res, candidates, MagicMock())
    assert result.is_fallback
    assert "Timeout exceeded" in result.fallback_reason
    assert result.chosen_id == "move_tackle"  # No verified fact; first legal action
    assert result.order == mock_order1


def test_fallback_rejects_stale_jev_response_before_submitting_order():
    order = MagicMock()
    candidates = {
        "move_a": CandidateAction("move_a", "move", "Move A", order, {})
    }
    response = JevDecisionResponse(model="jev", choice="move_a", confidence=0.9)
    metadata4 = BattleRequestMetadata(
        battle_id="battle-1",
        request_id="req-4",
        state_version=4,
        turn=4,
        request_type="move",
        force_switch=False,
        wait=False,
        trapped=False,
        maybe_trapped=False,
        deadline_monotonic=None,
    )
    metadata5 = BattleRequestMetadata(
        battle_id="battle-1",
        request_id="req-5",
        state_version=5,
        turn=5,
        request_type="move",
        force_switch=False,
        wait=False,
        trapped=False,
        maybe_trapped=False,
        deadline_monotonic=None,
    )

    stale = resolve_order(
        response,
        candidates,
        MagicMock(),
        expected_fingerprint=build_decision_fingerprint(metadata4, ("move_a",)),
        current_fingerprint=build_decision_fingerprint(metadata5, ("move_a",)),
    )

    assert stale.is_fallback is True
    assert "stale" in (stale.fallback_reason or "").lower()


def test_fallback_uses_exact_calculated_guaranteed_ko():
    first_order = MagicMock()
    ko_order = MagicMock()
    candidates = {
        "move_first": CandidateAction("move_first", "move", "First", first_order, {}),
        "move_ko": CandidateAction(
            "move_ko",
            "move",
            "Guaranteed KO",
            ko_order,
            {
                "accuracy": 100,
                "target_state": _fact("complete", "observed", "state"),
                "damage": _fact([100, 120], "calculated", "percent_of_target_max_hp"),
                "ko": _fact(True),
            },
        ),
    }

    result = select_deterministic_fallback(candidates, MagicMock(), "Jev error")

    assert result.chosen_id == "move_ko"
    assert result.order is ko_order


def test_fallback_avoids_verified_immediate_loss():
    losing_order = MagicMock()
    safe_order = MagicMock()
    candidates = {
        "move_loss": CandidateAction(
            "move_loss", "move", "Loses Now", losing_order, {"immediate_loss": _fact(True)}
        ),
        "move_safe": CandidateAction(
            "move_safe", "move", "Safe", safe_order, {"immediate_loss": _fact(False)}
        ),
    }

    result = select_deterministic_fallback(candidates, MagicMock(), "Jev error")

    assert result.chosen_id == "move_safe"


def test_fallback_preserves_the_only_known_check():
    ordinary_order = MagicMock()
    check_order = MagicMock()
    candidates = {
        "move_ordinary": CandidateAction(
            "move_ordinary", "move", "Ordinary", ordinary_order, {}
        ),
        "switch_check": CandidateAction(
            "switch_check",
            "switch",
            "Only Check",
            check_order,
            {"preserve_only_check": _fact(True, "observed")},
        ),
    }

    result = select_deterministic_fallback(candidates, MagicMock(), "Jev error")

    assert result.chosen_id == "switch_check"


def test_fallback_does_not_choose_large_heuristic_relative_estimate():
    first_order = MagicMock()
    heuristic_order = MagicMock()
    candidates = {
        "move_first": CandidateAction("move_first", "move", "First", first_order, {}),
        "move_heuristic": CandidateAction(
            "move_heuristic",
            "move",
            "Heuristic",
            heuristic_order,
            {
                "utility_estimate": {
                    "value": [999, 1000],
                    "source": "inferred",
                    "unit": "heuristic_relative_score",
                }
            },
        ),
    }

    result = select_deterministic_fallback(candidates, MagicMock(), "Jev error")

    assert result.chosen_id == "move_first"


def test_empty_candidates_use_a_current_legal_order():
    legal_order = MagicMock()
    battle = MagicMock()
    battle.valid_orders = [legal_order]

    result = select_deterministic_fallback({}, battle, "No candidates")

    assert result.is_fallback
    assert result.order is legal_order
    assert result.chosen_id == "legal_order_0"


def test_empty_candidates_without_orders_use_default_order():
    battle = MagicMock()
    battle.valid_orders = []

    result = select_deterministic_fallback({}, battle, "No candidates")

    assert result.is_fallback
    assert result.chosen_id == "emergency_default"
    assert result.order.message == "/choose default"
