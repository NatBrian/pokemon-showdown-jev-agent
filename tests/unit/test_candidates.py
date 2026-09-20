from unittest.mock import MagicMock
from jev_showdown.battle.candidates import CandidateAction, build_candidate_actions

def test_build_candidate_actions_moves_and_switches():
    mock_battle = MagicMock()
    mock_battle.can_tera = True
    
    # Mock active pokemon moves
    move1 = MagicMock()
    move1.id = "earthquake"
    move1.base_power = 100
    move1.type.name = "GROUND"
    move1.current_pp = 10
    
    move2 = MagicMock()
    move2.id = "swordsdance"
    move2.base_power = 0
    move2.type.name = "NORMAL"
    move2.current_pp = 20
    
    mock_battle.available_moves = [move1, move2]
    
    # Mock available switches
    switch1 = MagicMock()
    switch1.species = "Rotom-Wash"
    switch1.current_hp_fraction = 1.0
    mock_battle.available_switches = [switch1]
    
    candidates = build_candidate_actions(mock_battle)
    assert "move_earthquake" in candidates
    assert "move_swordsdance" in candidates
    assert "move_earthquake_tera" in candidates
    assert "switch_rotomwash" in candidates
    
    cand_eq = candidates["move_earthquake"]
    assert cand_eq.kind == "move"
    assert cand_eq.label == "Earthquake"
    
    cand_tera = candidates["move_earthquake_tera"]
    assert cand_tera.kind == "move_tera"
    assert cand_tera.label == "Earthquake (Terastallize)"
    
    cand_switch = candidates["switch_rotomwash"]
    assert cand_switch.kind == "switch"
    assert cand_switch.label == "Switch to Rotom-Wash"


def test_build_candidate_actions_keeps_duplicate_ids_unique():
    battle = MagicMock()
    battle.can_tera = False
    first = MagicMock()
    first.id = "tackle"
    first.base_power = 40
    first.type.name = "NORMAL"
    first.current_pp = 10
    second = MagicMock()
    second.id = "tackle"
    second.base_power = 40
    second.type.name = "NORMAL"
    second.current_pp = 10
    first_switch = MagicMock(spec=object)
    first_switch.species = "Rotom"
    first_switch.current_hp_fraction = 1.0
    second_switch = MagicMock(spec=object)
    second_switch.species = "Rotom"
    second_switch.current_hp_fraction = 0.8
    battle.available_moves = [first, second]
    battle.available_switches = [first_switch, second_switch]

    candidates = build_candidate_actions(battle)

    assert "move_tackle" in candidates
    assert "move_tackle_2" in candidates
    assert "switch_rotom" in candidates
    assert "switch_rotom_2" in candidates
