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
