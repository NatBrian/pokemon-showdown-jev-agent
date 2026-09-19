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
