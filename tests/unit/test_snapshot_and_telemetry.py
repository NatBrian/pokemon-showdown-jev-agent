# tests/unit/test_snapshot_and_telemetry.py
from unittest.mock import MagicMock
from jev_showdown.battle.snapshot import BattleSnapshotSerializer
from jev_showdown.telemetry.events import TurnHistoryTracker

def test_fog_of_war_opponent_team_tracking():
    mock_battle = MagicMock()
    mock_battle.turn = 3
    # Opponent active pokemon
    opp_mon = MagicMock()
    opp_mon.species = "Heatran"
    opp_mon.current_hp_fraction = 0.75
    opp_mon.status = None
    mock_battle.opponent_active_pokemon = opp_mon
    mock_battle.opponent_team = {"heatran": opp_mon}
    
    # Player team has 6 known mons
    player_mon = MagicMock()
    player_mon.species = "Garchomp"
    player_mon.current_hp_fraction = 1.0
    mock_battle.team = {f"mon_{i}": player_mon for i in range(6)}
    mock_battle.active_pokemon = player_mon
    
    serializer = BattleSnapshotSerializer()
    state = serializer.build_snapshot(mock_battle, {})
    
    assert state["state_schema"] == 1
    assert state["self"]["active_pokemon"]["species"] == "Garchomp"
    assert len(state["self"]["team"]) == 6
    
    # Opponent team should have 6 total slots: 1 revealed (Heatran), 5 unrevealed closed Pokeballs
    opp_team = state["opponent"]["team_slots"]
    assert len(opp_team) == 6
    assert opp_team[0]["revealed"] is True
    assert opp_team[0]["species"] == "Heatran"
    assert opp_team[1]["revealed"] is False
    assert opp_team[1]["species"] is None

def test_turn_history_tracker():
    tracker = TurnHistoryTracker()
    tracker.add_event(turn=1, actor="Garchomp", action="Earthquake", damage_pct=85, status=None)
    history = tracker.get_recent_events(limit=5)
    assert len(history) == 1
    assert history[0]["turn"] == 1
    assert history[0]["action"] == "Earthquake"
