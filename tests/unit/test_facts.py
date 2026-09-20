from types import SimpleNamespace
from unittest.mock import MagicMock

from poke_env.player.battle_order import SingleBattleOrder

from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.battle.facts import (
    annotate_candidates_with_facts,
    calculate_type_multiplier,
)


def _move_candidate(*, order_ref=None, facts=None):
    return CandidateAction(
        id="move_earthquake",
        kind="move",
        label="Earthquake",
        order_ref=order_ref or MagicMock(),
        facts=facts
        or {
            "base_power": 100,
            "type": "GROUND",
            "category": "PHYSICAL",
            "accuracy": 100,
            "priority": 0,
            "pp": 9,
        },
    )


def test_incomplete_state_uses_inferred_utility_and_keeps_damage_unknown():
    battle = MagicMock()
    battle.opponent_active_pokemon.type_1.name = "FIRE"
    battle.opponent_active_pokemon.type_2.name = "STEEL"
    battle.opponent_active_pokemon.current_hp_fraction = 0.8
    candidate = _move_candidate()

    criteria = annotate_candidates_with_facts(battle, {candidate.id: candidate})

    assert candidate.facts["type_multiplier"]["value"] == 4.0
    assert candidate.facts["type_multiplier"]["unit"] == "multiplier"
    assert candidate.facts["utility_estimate"]["unit"] == "heuristic_relative_score"
    assert candidate.facts["utility_estimate"]["source"] == "inferred"
    assert candidate.facts["damage"]["value"] is None
    assert candidate.facts["damage"]["source"] == "unknown"
    assert candidate.facts["ko"]["value"] is None
    assert "heuristic relative estimate" in criteria[candidate.id]
    assert "damage=unknown" in criteria[candidate.id]
    assert "4.0x effective" in criteria[candidate.id]


def test_annotate_uses_poke_env_damage_range_when_state_is_complete(monkeypatch):
    battle = MagicMock()
    active = MagicMock(identifier="p1a: Garchomp")
    opponent = MagicMock(
        identifier="p2a: Heatran",
        max_hp=200,
        current_hp_fraction=1.0,
        type_1=MagicMock(name="FIRE"),
        type_2=MagicMock(name="STEEL"),
    )
    battle.active_pokemon = active
    battle.opponent_active_pokemon = opponent
    battle.player_role = "p1"
    battle.opponent_role = "p2"
    move = MagicMock()
    move.id = "earthquake"
    move.base_power = 100
    move.type = MagicMock(name="GROUND")
    candidate = _move_candidate(
        order_ref=SingleBattleOrder(move),
        facts={"base_power": 100, "type": "GROUND", "category": "PHYSICAL"},
    )
    monkeypatch.setattr(
        "jev_showdown.battle.facts.calculate_damage",
        lambda attacker, defender, selected_move, selected_battle: (100, 120),
    )

    annotate_candidates_with_facts(battle, {candidate.id: candidate})

    assert candidate.facts["calculation_mode"] == "poke_env_gen9"
    assert candidate.facts["damage"] == {
        "value": [50, 60],
        "source": "calculated",
        "unit": "percent_of_target_max_hp",
        "confidence": 1.0,
        "assumptions": [
            "poke-env Gen 9 calculator",
            "current known battle stats and effects",
        ],
    }
    assert candidate.facts["ko"]["value"] is False
    assert candidate.facts["ko"]["source"] == "calculated"


def test_type_immunity_and_dual_type_multiplier_are_explicit():
    assert calculate_type_multiplier("ELECTRIC", "GROUND", None) == 0.0
    assert calculate_type_multiplier("GROUND", "FIRE", "STEEL") == 4.0


def test_move_metadata_and_switch_uncertainty_are_preserved():
    battle = MagicMock()
    battle.opponent_active_pokemon = None
    move = _move_candidate(
        facts={
            "base_power": 0,
            "type": "NORMAL",
            "category": "STATUS",
            "accuracy": 90,
            "priority": 1,
            "pp": 5,
        }
    )
    switch = CandidateAction(
        id="switch_rotom",
        kind="switch",
        label="Switch to Rotom",
        order_ref=MagicMock(),
        facts={"species": "Rotom", "hp_fraction": 0.75, "status": "PARALYZED"},
    )

    criteria = annotate_candidates_with_facts(
        battle, {move.id: move, switch.id: switch}
    )

    assert "accuracy=90%" in criteria[move.id]
    assert "priority=1" in criteria[move.id]
    assert "PP=5" in criteria[move.id]
    assert switch.facts["consequences"]["entry_hazard_damage"]["value"] is None
    assert (
        switch.facts["consequences"]["entry_hazard_damage"]["source"] == "unknown"
    )
    assert "HP: 75%" in criteria[switch.id]
    assert "PARALYZED" in criteria[switch.id]
