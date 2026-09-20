# tests/unit/test_agent.py
from unittest.mock import AsyncMock, MagicMock

import pytest
from poke_env.player import Player
from poke_env.player.battle_order import BattleOrder

from jev_showdown.agent import JevPlayer
from jev_showdown.config import Settings
from jev_showdown.decision.protocol import JevDecisionResponse


def _type_obj(name: str):
    t = MagicMock()
    t.name = name
    return t


def _make_move(move_id: str, base_power: int = 100, move_type: str = "GROUND",
               category: str = "PHYSICAL", accuracy: int = 100, current_pp: int = 10):
    move = MagicMock()
    move.id = move_id
    move.base_power = base_power
    move.type = _type_obj(move_type)
    move.category = _type_obj(category)
    move.accuracy = accuracy
    move.current_pp = current_pp
    return move


def _make_pokemon(species: str, hp_fraction: float = 1.0, status=None,
                  type_1: str = "NORMAL", type_2: str | None = None):
    mon = MagicMock()
    mon.species = species
    mon.current_hp_fraction = hp_fraction
    mon.status = status
    mon.fainted = False
    mon.type_1 = _type_obj(type_1)
    mon.type_2 = _type_obj(type_2) if type_2 else None
    return mon


def _make_battle(turn: int = 1):
    battle = MagicMock()
    battle.turn = turn
    battle.format = "gen9randombattle"
    battle.can_tera = False
    battle.weather = None
    battle.fields = []
    battle.active_pokemon = _make_pokemon("Garchomp", 1.0, None, "DRAGON", "GROUND")
    battle.team = {"garchomp": battle.active_pokemon}
    opp = _make_pokemon("Heatran", 1.0, None, "FIRE", "STEEL")
    battle.opponent_active_pokemon = opp
    battle.opponent_team = {"heatran": opp}
    battle.available_moves = [_make_move("earthquake")]
    battle.available_switches = [_make_pokemon("Rotom")]
    return battle


def _make_settings():
    return Settings(
        showdown_username=None,
        showdown_password=None,
        showdown_server_url="sim3.psim.us:8000",
        jev_endpoint="https://opencode.ai/zen/v1/systemone",
        jev_model="jev-1.13-free",
        jev_auth_token="Bearer public",
        jev_timeout_seconds=5.0,
        battle_format="gen9randombattle",
        dashboard_port=8000,
    )


@pytest.mark.asyncio
async def test_choose_move_orchestrates_jev_turn_loop():
    # Jev responses: (1) valid choice, (2) transport error, (3) invalid choice
    happy_res = JevDecisionResponse(
        model="jev-1.13-free",
        choice="move_earthquake",
        confidence=0.91,
        probabilities={"move_earthquake": 0.91, "switch_rotom": 0.09},
        latency_ms=42.0,
        input_tokens=309,
        output_tokens=24,
        cost="0",
        raw_response={"headers": {"Authorization": "Bearer secret-token"}},
        error=None,
    )
    error_res = JevDecisionResponse(
        model="jev-1.13-free",
        choice=None,
        confidence=0.0,
        error="Timeout exceeded",
    )
    invalid_res = JevDecisionResponse(
        model="jev-1.13-free",
        choice="move_not_a_real_candidate",
        confidence=0.5,
    )

    mock_client = MagicMock()
    mock_client.evaluate_decision = AsyncMock(
        side_effect=[happy_res, error_res, invalid_res]
    )

    events: list[dict] = []
    player = JevPlayer(
        settings=_make_settings(),
        jev_client=mock_client,
        on_turn_event=events.append,
        start_listening=False,
    )
    assert isinstance(player, Player)

    battle = _make_battle(turn=3)

    # --- 1) Happy path: Jev's valid choice is validated and returned ---
    order = await player.choose_move(battle)
    assert isinstance(order, BattleOrder)

    # Jev was queried with the serialized snapshot and deterministic criteria
    first_call = mock_client.evaluate_decision.await_args
    state = first_call.kwargs["state"]
    criteria = first_call.kwargs["criteria"]
    assert state["state_schema"] == 1
    assert state["turn"] == 3
    assert state["self"]["active_pokemon"]["species"] == "Garchomp"
    assert "move_earthquake" in criteria
    assert criteria["move_earthquake"].startswith("Earthquake")

    # Telemetry dispatched with the validated choice
    assert len(events) == 1
    event = events[0]
    assert event["turn"] == 3
    assert event["chosen_id"] == "move_earthquake"
    assert event["is_fallback"] is False
    assert event["jev"]["confidence"] == 0.91
    assert event["jev"]["error"] is None
    assert event["jev_request"]["model"] == "jev-1.13-free"
    assert event["jev_request"]["state"] == state
    assert event["jev_request"]["questions"]["action"]["criteria"] == criteria
    assert event["jev_response"]["choice"] == "move_earthquake"
    assert "secret-token" not in str(event["jev_response"])
    assert "Authorization" not in str(event["jev_response"])
    assert event["submitted_order"]["message"] == order.message

    # Turn history tracked for the active pokemon
    assert len(player.history_tracker.events) == 1
    assert player.history_tracker.events[0]["turn"] == 3
    assert player.history_tracker.events[0]["actor"] == "Garchomp"
    assert player.history_tracker.events[0]["action"] == "Earthquake"

    # --- 2) Fallback: Jev transport error resolves to a deterministic order ---
    order = await player.choose_move(battle)
    assert isinstance(order, BattleOrder)
    assert events[1]["is_fallback"] is True
    assert "Timeout exceeded" in events[1]["fallback_reason"]
    assert events[1]["chosen_id"] == "move_earthquake"  # best damage heuristic
    assert events[1]["jev"]["error"] == "Timeout exceeded"

    # --- 3) Fallback: Jev picks an illegal candidate ---
    order = await player.choose_move(battle)
    assert isinstance(order, BattleOrder)
    assert events[2]["is_fallback"] is True
    assert "Invalid choice" in events[2]["fallback_reason"]
    assert events[2]["chosen_id"] == "move_earthquake"

    # Three turns tracked end-to-end
    assert len(player.history_tracker.events) == 3
    assert mock_client.evaluate_decision.await_count == 3


@pytest.mark.asyncio
async def test_choose_move_emits_correlated_decision_phases():
    response = JevDecisionResponse(
        model="jev-1.13-free",
        choice="move_earthquake",
        confidence=0.91,
        probabilities={"move_earthquake": 0.91, "switch_rotom": 0.09},
        latency_ms=42.0,
        input_tokens=309,
        output_tokens=24,
        cost="0",
    )
    mock_client = MagicMock()
    mock_client.evaluate_decision = AsyncMock(return_value=response)

    phases: list[dict] = []
    turn_events: list[dict] = []
    player = JevPlayer(
        settings=_make_settings(),
        jev_client=mock_client,
        on_decision_phase=phases.append,
        on_turn_event=turn_events.append,
        start_listening=False,
    )
    battle = _make_battle(turn=3)
    battle.battle_tag = "battle-gen9randombattle-phase-1"

    order = await player.choose_move(battle)

    assert isinstance(order, BattleOrder)
    assert [event["phase"] for event in phases] == [
        "EXTRACTING",
        "CALCULATING",
        "JEV_EVALUATING",
        "LEGAL",
        "ORDER_SUBMITTED",
        "AWAITING_SHOWDOWN",
    ]
    decision_ids = {event["decision_id"] for event in phases}
    assert len(decision_ids) == 1
    assert turn_events[0]["decision_id"] in decision_ids

    evaluating = next(event for event in phases if event["phase"] == "JEV_EVALUATING")
    assert evaluating["request_payload"]["model"] == "jev-1.13-free"
    assert evaluating["request_payload"]["state"] == evaluating["snapshot"]

    legal = next(event for event in phases if event["phase"] == "LEGAL")
    assert legal["is_fallback"] is False
    assert legal["validation"]["chosen_id"] == "move_earthquake"

    submitted = next(
        event for event in phases if event["phase"] == "ORDER_SUBMITTED"
    )
    assert submitted["submitted_order"]["message"] == order.message


@pytest.mark.asyncio
async def test_protocol_result_emits_once_for_pending_decision():
    response = JevDecisionResponse(
        model="jev-1.13-free",
        choice="move_earthquake",
        confidence=0.91,
        probabilities={"move_earthquake": 0.91},
        latency_ms=42.0,
    )
    mock_client = MagicMock()
    mock_client.evaluate_decision = AsyncMock(return_value=response)
    phases: list[dict] = []
    player = JevPlayer(
        settings=_make_settings(),
        jev_client=mock_client,
        on_decision_phase=phases.append,
        start_listening=False,
    )
    battle = _make_battle(turn=3)
    battle.battle_tag = "battle-gen9randombattle-result-1"
    battle.player_role = "p1"
    player._battles[battle.battle_tag] = battle

    await player.choose_move(battle)
    await player._handle_battle_message(
        [
            [">battle-gen9randombattle-result-1"],
            ["", "move", "p1a: Garchomp", "Earthquake", "p2a: Heatran"],
            ["", "-damage", "p2a: Heatran", "0/344"],
        ]
    )
    await player._handle_battle_message(
        [[">battle-gen9randombattle-result-1"], ["", "turn", "4"]]
    )

    observed = [event for event in phases if event["phase"] == "RESULT_OBSERVED"]
    assert len(observed) == 1
    assert observed[0]["observed_commands"] == ["move", "-damage"]


@pytest.mark.asyncio
async def test_new_battle_resets_history_tracker(monkeypatch):
    player = JevPlayer(
        settings=_make_settings(),
        jev_client=MagicMock(),
        start_listening=False,
    )
    player.history_tracker.add_event(1, "Garchomp", "Earthquake")

    async def fake_create_battle(_self, _split_message):
        battle = MagicMock()
        battle.battle_tag = "battle-gen9randombattle-new"
        return battle

    monkeypatch.setattr(Player, "_create_battle", fake_create_battle)

    await player._create_battle([[">battle-gen9randombattle-new", "start"]])

    assert player.history_tracker.events == []


@pytest.mark.asyncio
async def test_battle_finished_emits_battle_end_event():
    battle_events: list[dict] = []
    player = JevPlayer(
        settings=_make_settings(),
        jev_client=MagicMock(),
        on_battle_event=battle_events.append,
        start_listening=False,
    )
    battle = _make_battle(turn=9)
    battle.battle_tag = "battle-gen9randombattle-1"
    battle.won = True
    battle.players = ("JevPlayer 1", "Opponent 9")
    battle.player_username = "JevPlayer 1"
    player._battles["battle-gen9randombattle-1"] = battle

    player._battle_finished_callback(battle)

    assert len(battle_events) == 1
    event = battle_events[0]
    assert event["type"] == "BATTLE_END"
    assert event["won"] is True
    assert event["total_turns"] == 9
    assert event["winner"] == "JevPlayer 1"
    assert event["battle_format"] == "gen9randombattle"


@pytest.mark.asyncio
async def test_battle_finished_loses_reports_lose():
    battle_events: list[dict] = []
    player = JevPlayer(
        settings=_make_settings(),
        jev_client=MagicMock(),
        on_battle_event=battle_events.append,
        start_listening=False,
    )
    battle = _make_battle()
    battle.battle_tag = "battle-gen9randombattle-2"
    battle.won = False
    battle.players = ("JevPlayer 1", "Opponent 9")
    battle.player_username = "JevPlayer 1"

    player._battle_finished_callback(battle)

    assert battle_events[0]["type"] == "BATTLE_END"
    assert battle_events[0]["won"] is False
    assert battle_events[0]["winner"] == "Opponent 9"


@pytest.mark.asyncio
async def test_battle_message_scanning_enriches_history():
    player = JevPlayer(
        settings=_make_settings(),
        jev_client=MagicMock(),
        start_listening=False,
    )
    battle = _make_battle()
    battle.battle_tag = "battle-gen9randombattle-1"
    battle.player_role = "p1"
    player._battles["battle-gen9randombattle-1"] = battle

    request_json = (
        '{"side": {"pokemon": ['
        '{"ident": "p1a: Garchomp", "condition": "357/357"}, '
        '{"ident": "p2a: Heatran", "condition": "344/344"}]}}'
    )
    split_messages = [
        [">battle-gen9randombattle-1", "start"],
        ["", "request", request_json],
        ["", "-move", "p2a: Heatran", "scald", "p1a: Garchomp"],
        ["", "-damage", "p1a: Garchomp", "286/357"],
        # The next turn marker closes (and flushes) the turn-1 actions.
        ["", "turn", "2"],
    ]
    await player._handle_battle_message(split_messages)

    events = player.history_tracker.events
    assert len(events) == 1
    event = events[0]
    assert event["actor"] == "Opponent"
    assert event["action"] == "Scald"
    assert event["damage_pct"] == 20  # (357 - 286) / 357


@pytest.mark.asyncio
async def test_battle_message_emits_raw_battle_frame():
    frames: list[dict] = []
    player = JevPlayer(
        settings=_make_settings(),
        jev_client=MagicMock(),
        on_battle_frame=frames.append,
        start_listening=False,
    )
    battle = _make_battle()
    battle.battle_tag = "battle-gen9randombattle-1"
    battle.player_role = "p1"
    player._battles[battle.battle_tag] = battle

    await player._handle_battle_message(
        [
            [">battle-gen9randombattle-1"],
            ["", "turn", "2"],
            ["", "-damage", "p1a: Garchomp", "250/357"],
        ]
    )

    assert frames == [
        {
            "type": "BATTLE_FRAME",
            "battle_tag": "battle-gen9randombattle-1",
            "lines": ["|turn|2", "|-damage|p1a: Garchomp|250/357"],
        }
    ]


@pytest.mark.asyncio
async def test_own_side_move_scanner_event_merges_into_decision():
    player = JevPlayer(
        settings=_make_settings(),
        jev_client=MagicMock(),
        start_listening=False,
    )
    battle = _make_battle(turn=4)
    battle.battle_tag = "battle-gen9randombattle-1"
    battle.player_role = "p1"
    player._battles["battle-gen9randombattle-1"] = battle

    request_json = (
        '{"side": {"pokemon": ['
        '{"ident": "p1a: Garchomp", "condition": "357/357"}, '
        '{"ident": "p2a: Heatran", "condition": "344/344"}]}}'
    )

    # Turn 4 starts; the request arrives and choose_move records the
    # decision card for this turn.
    await player._handle_battle_message(
        [
            [">battle-gen9randombattle-1", "start"],
            ["", "turn", "4"],
            ["", "request", request_json],
        ]
    )
    player.history_tracker.add_event(
        turn=4, actor="Garchomp", action="Earthquake", note="confidence=0.90"
    )

    # Turn 4 resolution: opponent (faster) acts first, then our move echoes
    # back; the next turn marker closes both actions.
    await player._handle_battle_message(
        [
            [">battle-gen9randombattle-1", "x"],
            ["", "-move", "p2a: Heatran", "scald", "p1a: Garchomp"],
            ["", "-damage", "p1a: Garchomp", "300/357"],
            ["", "-move", "p1a: Garchomp", "earthquake", "p2a: Heatran"],
            ["", "-damage", "p2a: Heatran", "261/344"],
            ["", "turn", "5"],
        ]
    )

    events = player.history_tracker.events
    # One decision card for us (scanned echo merged in) + one opponent card.
    assert len(events) == 2
    ours = events[0]
    assert ours["actor"] == "Garchomp"
    assert ours["action"] == "Earthquake"
    assert ours["damage_pct"] == 24  # merged from the battle echo
    assert ours["note"] == "confidence=0.90"
    theirs = events[1]
    assert theirs["actor"] == "Opponent"
    assert theirs["action"] == "Scald"
    assert theirs["damage_pct"] == 16
