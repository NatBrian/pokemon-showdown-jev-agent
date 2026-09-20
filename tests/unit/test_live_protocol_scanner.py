# tests/unit/test_live_protocol_scanner.py
"""Reproduce the REAL Showdown wire-protocol sequence through JevPlayer.

The live battle showed zero scanner events in recent_history, while the
synthetic unit tests pass. This test feeds the exact line structure the
public server sends (tag-only first line, |init block, per-turn resolution
chunks, |request payloads) to find the discrepancy.
"""
import json

from poke_env.player import Player  # noqa: F401  (import sanity)

from jev_showdown.agent import JevPlayer
from jev_showdown.config import Settings
from jev_showdown.decision.protocol import JevDecisionResponse

from tests.unit.test_agent import _make_battle, _make_settings  # reuse helpers


def _client(responses):
    from unittest.mock import AsyncMock, MagicMock

    c = MagicMock()
    c.evaluate_decision = AsyncMock(side_effect=list(responses))
    return c


def _resp(choice="move_aquacutter"):
    return JevDecisionResponse(
        model="jev-1.13-free",
        choice=choice,
        confidence=0.9,
        probabilities={choice: 0.9},
        latency_ms=10.0,
        input_tokens=100,
        output_tokens=10,
        cost="0",
        error=None,
    )


def _request(turn: int) -> str:
    """A poke-env-compatible |request payload (same shape as the e2e server)."""
    return json.dumps(
        {
            "side": {
                "id": "p1",
                "name": "1j_e_v1",
                "pokemon": [
                    {
                        "ident": "p1: Oranguru",
                        "details": "Oranguru",
                        "active": True,
                        "baseAbility": "No Ability",
                        "ability": "No Ability",
                        "condition": "315/315",
                        "item": "",
                        "moves": ["focus blast", "hurricane"],
                        "status": "",
                    },
                    {
                        "ident": "p2: Veluza",
                        "details": "Veluza",
                        "active": False,
                        "baseAbility": "No Ability",
                        "ability": "No Ability",
                        "condition": "252/252",
                        "item": "",
                        "moves": ["aquacutter"],
                        "status": "",
                    },
                ],
            },
            "active": [
                {
                    "moves": [
                        {
                            "id": "focusblast",
                            "pp": 10,
                            "maxpp": 10,
                            "type": "Psychic",
                            "disabled": False,
                            "noClick": False,
                            "target": "normal",
                            "sourcePosition": 1,
                        },
                        {
                            "id": "hurricane",
                            "pp": 10,
                            "maxpp": 10,
                            "type": "Flying",
                            "disabled": False,
                            "noClick": False,
                            "target": "normal",
                            "sourcePosition": 1,
                        },
                    ],
                    "trapped": False,
                    "canMegaEvo": False,
                    "canZMove": False,
                    "canDynamax": False,
                    "canTerastallize": False,
                    "maybeTrapped": False,
                    "mustMove": True,
                }
            ],
            "forceSwitch": [False],
            "rqid": f"req{turn}",
        }
    )


async def test_real_protocol_sequence_produces_scanner_events():
    events = []
    player = JevPlayer(
        settings=_make_settings(),
        jev_client=_client([_resp() for _ in range(3)]),
        on_turn_event=events.append,
        start_listening=False,
        battle_format="gen9randombattle",
    )

    tag = "battle-gen9randombattle-123"

    class _FakeWS:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, text: str) -> None:
            self.sent.append(text)

    player.ps_client.websocket = _FakeWS()

    # 1) init message: tag-only first line, then |init block. Real battles
    # send initial |switch| lines (HP seeds) and a |turn|1 marker.
    await player._handle_battle_message(
        [m.split("|") for m in
         [
             ">battle-gen9randombattle-123",
             "|init",
             "|player|p1|1j_e_v1||",
             "|player|p2|opponent||",
             "|switch|p1a: Oranguru|Oranguru|315/315",
             "|switch|p2a: Dudunsparce|Dudunsparce|100/100",
             "|start",
             "|turn|1",
         ]]
    )
    assert tag in player.battles, "battle must be created from init message"
    battle = player.battles[tag]
    print("player_role:", battle.player_role)

    # 2) request for turn 1 -> choose_move
    await player._handle_battle_message(
        [m.split("|") for m in [f">battle-gen9randombattle-123", f"|request|{_request(1)}"]]
    )
    assert len(events) == 1

    # 3) turn-1 resolution: opponent moves first, then us, then damage.
    # Real protocol: tag-only first line, content on following lines;
    # |move|/|faint| have NO dash; |-damage| is dashed.
    await player._handle_battle_message(
        [m.split("|") for m in
         [
             ">battle-gen9randombattle-123",
             "|move| p2a: Dudunsparce|Wood Hammer|p1a: Oranguru",
             "|-damage| p1a: Oranguru|150/315",
             "|move| p1a: Oranguru|Focus Blast|p2a: Dudunsparce",
             "|-damage| p2a: Dudunsparce|0/100",
             "|faint| p2a: Dudunsparce",
         ]]
    )

    # 4) turn 2 marker + request -> decision 2 (scanner events for turn 1 flush here)
    await player._handle_battle_message(
        [m.split("|") for m in [">battle-gen9randombattle-123", "|turn|2", f"|request|{_request(2)}"]]
    )
    assert len(events) == 2

    hist = events[1]["recent_history"]
    print("history:", [(h.get("turn"), h.get("actor"), h.get("action"), h.get("damage_pct")) for h in hist])

    # The opponent's turn-1 action must be its own card, with damage.
    opp_cards = [h for h in hist if h.get("actor") == "Opponent"]
    assert opp_cards, "opponent action card must appear in recent_history"
    assert any(h.get("damage_pct") for h in opp_cards), "opponent card must carry damage"

    # Our own turn-1 move must be merged into the decision card (damage, not a dup).
    ours = [h for h in hist if h.get("actor", "").lower() == "oranguru" and h.get("turn") == 1]
    assert len(ours) == 1, "our move must merge into the decision card, not duplicate"
    assert ours[0].get("damage_pct"), "our decision card must carry damage"


async def test_real_protocol_result_phase_uses_command_names_only():
    phases: list[dict] = []
    player = JevPlayer(
        settings=_make_settings(),
        jev_client=_client([_resp()]),
        on_decision_phase=phases.append,
        start_listening=False,
        battle_format="gen9randombattle",
    )
    tag = "battle-gen9randombattle-phase-123"
    battle = _make_battle(turn=1)
    battle.battle_tag = tag
    battle.player_role = "p1"
    player._battles[tag] = battle

    await player.choose_move(battle)
    await player._handle_battle_message(
        [
            [f">{tag}"],
            ["", "move", "p1a: Garchomp", "Earthquake", "p2a: Heatran"],
            ["", "-damage", "p2a: Heatran", "0/344"],
        ]
    )

    observed = [event for event in phases if event["phase"] == "RESULT_OBSERVED"]
    assert len(observed) == 1
    assert observed[0]["observed_commands"] == ["move", "-damage"]
    assert "Heatran" not in str(observed[0])
