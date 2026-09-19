from unittest.mock import MagicMock
from poke_env.battle import AbstractBattle
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
