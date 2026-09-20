# tests/unit/test_validator_and_fallback.py
from unittest.mock import MagicMock
from poke_env.battle import AbstractBattle
from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.decision.protocol import JevDecisionResponse
from jev_showdown.strategy.fallback import resolve_order, select_deterministic_fallback

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
    assert result.chosen_id == "move_earthquake"  # Highest power fallback
    assert result.order == mock_order2


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
