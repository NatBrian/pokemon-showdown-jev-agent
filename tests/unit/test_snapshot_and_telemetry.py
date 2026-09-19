# tests/unit/test_snapshot_and_telemetry.py
from unittest.mock import MagicMock
from jev_showdown.battle.snapshot import BattleSnapshotSerializer
from jev_showdown.telemetry.events import BattleEventScanner, TurnHistoryTracker

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

def test_turn_history_tracker_badges_and_faint():
    tracker = TurnHistoryTracker()
    tracker.add_event(
        turn=2,
        actor="Garchomp",
        action="Swords Dance",
        fainted=False,
        badges=["ATK +2"],
    )
    event = tracker.events[0]
    assert event["badges"] == ["ATK +2"]
    assert event["fainted"] is False

def test_battle_event_scanner_move_damage_status_faint():
    scanner = BattleEventScanner()
    events = []
    events += scanner.feed_lines(
        [
            '|request|{"side": {"pokemon": ['
            '{"ident": "p1a: Garchomp", "condition": "357/357"}, '
            '{"ident": "p2a: Heatran", "condition": "344/344"}]}}',
            "|turn|2",
            "|-move| p1a: Garchomp|earthquake|p2a: Heatran",
            "|-damage| p2a: Heatran|261/344",
            "|-move| p2a: Heatran|magma storm|p1a: Garchomp",
            "|-status| p1a: Garchomp|brn",
            "|-damage| p1a: Garchomp|180/357",
            "|-faint| p2a: Heatran",
        ]
    )
    # The next turn marker flushes the still-open actions.
    events += scanner.feed_lines(["|turn|3"])

    assert len(events) == 2
    earthquake, magma_storm = events

    # Our move: damage computed against the opponent's true max HP.
    assert earthquake["actor"] == "p1a: Garchomp"
    assert earthquake["side"] == "p1"
    assert earthquake["kind"] == "move"
    assert earthquake["action"] == "Earthquake"
    assert earthquake["turn"] == 2
    assert earthquake["damage_pct"] == 24  # (344 - 261) / 344
    assert earthquake["fainted"] is True  # Heatran fainted

    # Opponent's move: burn + damage on our side.
    assert magma_storm["actor"] == "p2a: Heatran"
    assert magma_storm["side"] == "p2"
    assert magma_storm["action"] == "Magma Storm"
    assert magma_storm["damage_pct"] == 50  # (357 - 180) / 357
    assert magma_storm["status"] == "BURN"
    assert magma_storm["fainted"] is False

def test_battle_event_scanner_stat_badges_and_switch():
    scanner = BattleEventScanner()
    events = scanner.feed_lines(
        [
            # The battle must be live (a request has been received) for
            # switches to produce cards; initial send-outs do not.
            "|request|{}",
            "|move| p1a: Garchomp|swords dance|p2a: Heatran",
            "|-stat| p1a: Garchomp|atk|2",
            "|switch| p2a: Rotom-Wash|Rotom-Wash|123/123",
            "|-stat| p1a: Garchomp|atk|-1",
            "|turn|2",
        ]
    )
    assert len(events) == 2
    swords_dance, switch = events
    assert swords_dance["badges"] == ["ATK +2"]
    assert switch["kind"] == "switch"
    assert switch["action"] == "Switch"
    assert switch["actor"] == "p2a: Rotom-Wash"
    assert switch["badges"] == ["ATK -1"]

def test_battle_event_scanner_ignores_garbage():
    scanner = BattleEventScanner()
    # Malformed or unknown lines must not raise or emit events.
    events = scanner.feed_lines(
        [
            "||",
            "|-move| p1a: Garchomp",  # missing move id
            "|-damage| p1a: Garchomp|not-a-number",
            "|weather|rain",
        ]
    )
    assert events == []
