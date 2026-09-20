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
    
    assert state["state_schema"] == 2
    assert state["self"]["active_pokemon"]["species"] == "Garchomp"
    assert len(state["self"]["team"]) == 6
    
    # Opponent team should have 6 total slots: 1 revealed (Heatran), 5 unrevealed closed Pokeballs
    opp_team = state["opponent"]["team_slots"]
    assert len(opp_team) == 6
    assert opp_team[0]["revealed"] is True
    assert opp_team[0]["species"] == "Heatran"
    assert opp_team[1]["revealed"] is False
    assert opp_team[1]["species"] is None


def test_snapshot_includes_observable_boosts_effects_and_side_conditions():
    battle = MagicMock()
    battle.turn = 4
    sunny = MagicMock()
    sunny.name = "SUNNYDAY"
    battle.weather = {sunny: 1}
    battle.fields = []
    battle.can_tera = True
    battle.side_conditions = {"stealthrock": 1}
    battle.opponent_side_conditions = {"spikes": 2}
    active = MagicMock()
    active.species = "Garchomp"
    active.current_hp_fraction = 0.75
    active.status = None
    active.fainted = False
    active.boosts = {"atk": 2, "spe": -1}
    active.effects = {"protect": 1}
    active.type_1 = MagicMock(name="DRAGON")
    active.type_2 = MagicMock(name="GROUND")
    battle.active_pokemon = active
    battle.team = {"garchomp": active}
    battle.opponent_active_pokemon = None
    battle.opponent_team = {}

    state = BattleSnapshotSerializer().build_snapshot(battle, {})

    assert state["side_conditions"]["self"] == {"stealthrock": 1}
    assert state["side_conditions"]["opponent"] == {"spikes": 2}
    assert state["weather"] == "SUNNYDAY"
    assert state["self"]["active_pokemon"]["boosts"] == {"atk": 2, "spe": -1}
    assert state["self"]["active_pokemon"]["effects"] == ["protect"]


def test_snapshot_v2_contains_request_history_beliefs_responses_and_safe_actions():
    from jev_showdown.battle.contracts import BattleRequestMetadata
    from jev_showdown.battle.candidates import CandidateAction

    battle = MagicMock()
    battle.turn = 4
    battle.battle_tag = "battle-gen9randombattle-1"
    battle.format = "gen9randombattle"
    battle.last_request = {
        "rqid": "req-4",
        "active": [{
            "moves": [{"id": "earthquake", "pp": 8, "maxpp": 16, "disabled": False}],
        }],
    }
    battle.force_switch = False
    battle.wait = False
    battle.trapped = False
    battle.maybe_trapped = False
    battle.can_tera = True
    battle.weather = None
    battle.fields = []
    battle.side_conditions = {}
    battle.opponent_side_conditions = {}
    battle.active_pokemon = MagicMock(spec=[])
    battle.active_pokemon.species = "Garchomp"
    battle.active_pokemon.moves = {
        "earthquake": MagicMock(
            id="earthquake", current_pp=8, max_pp=16, disabled=False
        )
    }
    battle.team = {"garchomp": battle.active_pokemon}
    battle.opponent_active_pokemon = None
    battle.opponent_team = {}

    candidate = CandidateAction(
        id="move_a",
        kind="move",
        label="Move A",
        order_ref=MagicMock(name="hidden-order"),
        facts={
            "damage": {
                "value": [40, 50],
                "source": "calculated",
                "unit": "percent_of_target_max_hp",
            }
        },
    )
    metadata = BattleRequestMetadata(
        battle_id="battle-gen9randombattle-1",
        request_id="req-4",
        state_version=4,
        turn=4,
        request_type="move",
        force_switch=False,
        wait=False,
        trapped=False,
        maybe_trapped=False,
        deadline_monotonic=123.0,
    )
    beliefs = {"opponent_slots": [{"visibility": "unknown_slot"}] * 6}
    consequences = {"move_a": {"opponent_stays": {"source": "unknown"}}}

    state = BattleSnapshotSerializer().build_snapshot(
        battle,
        {candidate.id: candidate},
        metadata=metadata,
        criteria={"move_a": "Move A; legal action."},
        recent_history=[{"turn": 4, "action": "Earthquake"}],
        beliefs=beliefs,
        consequences=consequences,
    )

    import json

    assert state["state_schema"] == 2
    assert state["request"]["rqid"] == "req-4"
    assert state["request"]["force_switch"] is False
    assert state["request"]["state_version"] == 4
    assert state["request"]["deadline_monotonic"] == 123.0
    assert state["history"][-1]["action"] == "Earthquake"
    assert "beliefs" in state
    assert "opponent_responses" in state
    assert state["glossary"]["switch"]
    assert state["legal_actions"][0]["id"] == "move_a"
    assert state["criteria"]["move_a"].startswith("Move A")
    assert state["self"]["active_pokemon"]["moves"][0]["pp"] == 8
    assert state["self"]["active_pokemon"]["moves"][0]["disabled"] is False
    assert len(state["beliefs"]["opponent_slots"]) == 6
    assert "hidden-order" not in json.dumps(state, default=str)
    json.dumps(state)

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
