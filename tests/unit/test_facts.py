from unittest.mock import MagicMock
from poke_env.battle import AbstractBattle
from poke_env.player.battle_order import SingleBattleOrder
from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.battle.facts import annotate_candidates_with_facts

def test_annotate_candidates_with_facts():
    mock_battle = MagicMock()
    mock_battle.opponent_active_pokemon.type_1.name = "FIRE"
    mock_battle.opponent_active_pokemon.type_2.name = "STEEL"
    mock_battle.opponent_active_pokemon.current_hp_fraction = 0.8

    mock_order = MagicMock()
    candidate = CandidateAction(
        id="move_earthquake",
        kind="move",
        label="Earthquake",
        order_ref=mock_order,
        facts={"base_power": 100, "type": "GROUND", "category": "PHYSICAL", "accuracy": 100}
    )
    candidates = {"move_earthquake": candidate}

    criteria = annotate_candidates_with_facts(mock_battle, candidates)

    assert "move_earthquake" in criteria
    assert "type_multiplier" in candidate.facts
    assert candidate.facts["type_multiplier"] == 4.0  # Ground vs Fire/Steel is 4x
    assert "4.0x effective" in criteria["move_earthquake"]


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
    candidate = CandidateAction(
        id="move_earthquake",
        kind="move",
        label="Earthquake",
        order_ref=SingleBattleOrder(move),
        facts={"base_power": 100, "type": "GROUND", "category": "PHYSICAL"},
    )
    monkeypatch.setattr(
        "jev_showdown.battle.facts.calculate_damage",
        lambda attacker, defender, selected_move, selected_battle: (100, 120),
    )

    annotate_candidates_with_facts(battle, {candidate.id: candidate})

    assert candidate.facts["calculation_mode"] == "poke_env_gen9"
    assert candidate.facts["estimated_damage_range"] == [50, 60]
    assert candidate.facts["estimated_ko"] is False
