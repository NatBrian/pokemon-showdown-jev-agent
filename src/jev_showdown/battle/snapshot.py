from collections.abc import Mapping
from typing import Any

from poke_env.battle import AbstractBattle

from jev_showdown.battle.beliefs import build_hidden_information_ledger
from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.battle.contracts import BattleRequestMetadata, Fact
from jev_showdown.battle.state import extract_request_metadata
from jev_showdown.telemetry.serialization import json_safe as _json_safe


def _enum_name(value: Any) -> str | None:
    raw = getattr(value, "name", value)
    if isinstance(raw, str):
        return raw
    return None


def _condition_map(values: Any) -> dict[str, Any]:
    if not isinstance(values, Mapping):
        return {}
    result: dict[str, Any] = {}
    for key, value in values.items():
        name = _enum_name(key) or str(key)
        if isinstance(value, (bool, int, float, str)) or value is None:
            result[name] = value
        else:
            result[name] = _enum_name(value) or str(value)
    return result


def _effect_names(values: Any) -> list[str]:
    if isinstance(values, Mapping):
        values = list(values.keys())
    if not isinstance(values, (list, set, tuple)):
        return []
    return [name for value in values if (name := (_enum_name(value) or str(value)))]


def _move_view(mon: Any) -> list[dict[str, Any]]:
    raw_moves = getattr(mon, "moves", {})
    if isinstance(raw_moves, Mapping):
        items = list(raw_moves.items())
    elif isinstance(raw_moves, (list, tuple, set)):
        items = [(None, move) for move in raw_moves]
    else:
        items = []

    result: list[dict[str, Any]] = []
    for key, move in items:
        move_id = key if isinstance(key, str) else getattr(move, "id", None)
        if not isinstance(move_id, str):
            continue
        current_pp = getattr(move, "current_pp", None)
        max_pp = getattr(move, "max_pp", None)
        disabled = getattr(move, "disabled", None)
        result.append(
            {
                "id": move_id,
                "pp": current_pp if isinstance(current_pp, (int, float)) else None,
                "max_pp": max_pp if isinstance(max_pp, (int, float)) else None,
                "disabled": disabled if isinstance(disabled, bool) else None,
            }
        )
    return result


def _request_move_view(battle: AbstractBattle) -> list[dict[str, Any]]:
    request = getattr(battle, "last_request", None)
    if not isinstance(request, Mapping):
        return []
    active = request.get("active")
    if not isinstance(active, list) or not active or not isinstance(active[0], Mapping):
        return []
    moves = active[0].get("moves")
    if not isinstance(moves, list):
        return []
    result: list[dict[str, Any]] = []
    for move in moves:
        if not isinstance(move, Mapping) or not isinstance(move.get("id"), str):
            continue
        result.append(
            {
                "id": move["id"],
                "pp": move.get("pp"),
                "max_pp": move.get("maxpp"),
                "disabled": move.get("disabled")
                if isinstance(move.get("disabled"), bool)
                else None,
            }
        )
    return result


def _mon_view(mon: Any, *, revealed: bool = True, active: bool = False, battle: Any = None) -> dict[str, Any]:
    """Serialize a poke-env Pokemon without exposing protocol/order objects."""
    if mon is None or not revealed:
        return {
            "revealed": revealed,
            "species": None,
            "hp_fraction": None,
            "hp": None,
            "max_hp": None,
            "level": None,
            "fainted": False,
            "status": None,
            "moves": [],
        }
    status = _enum_name(getattr(mon, "status", None))
    types = []
    for type_value in (getattr(mon, "type_1", None), getattr(mon, "type_2", None)):
        type_name = _enum_name(type_value)
        if type_name:
            types.append(type_name)
    moves = _move_view(mon)
    if active and not moves and battle is not None:
        moves = _request_move_view(battle)
    return {
        "revealed": True,
        "species": str(getattr(mon, "species", "Unknown")),
        "hp_fraction": getattr(mon, "current_hp_fraction", None),
        "hp": getattr(mon, "current_hp", None),
        "max_hp": getattr(mon, "max_hp", None),
        "level": getattr(mon, "level", None),
        "fainted": bool(getattr(mon, "fainted", False)),
        "status": status,
        "types": types,
        "boosts": _condition_map(getattr(mon, "boosts", {})),
        "effects": _effect_names(getattr(mon, "effects", set())),
        "moves": moves,
    }


def _request_view(metadata: BattleRequestMetadata) -> dict[str, Any]:
    return {
        "battle_id": metadata.battle_id,
        "rqid": metadata.request_id,
        "state_version": metadata.state_version,
        "turn": metadata.turn,
        "request_type": metadata.request_type,
        "force_switch": metadata.force_switch,
        "wait": metadata.wait,
        "trapped": metadata.trapped,
        "maybe_trapped": metadata.maybe_trapped,
        "deadline_monotonic": metadata.deadline_monotonic,
    }


def _hypotheses(turn: int) -> dict[str, dict[str, Any]]:
    phase = "opening" if turn <= 3 else "midgame"
    return {
        "current_phase": Fact(
            phase, "inferred", "battle_phase", None, ("turn number only",)
        ).to_dict(),
        "possible_win_plans": Fact(
            None,
            "unknown",
            "plan_list",
            assumptions=("a win plan requires position-specific evaluation",),
        ).to_dict(),
        "lose_condition_threats": Fact(
            None,
            "unknown",
            "threat_list",
            assumptions=("no unsupported threat is asserted",),
        ).to_dict(),
        "resource_criticality": Fact(
            None,
            "unknown",
            "resource_list",
            assumptions=("resource value is position-dependent",),
        ).to_dict(),
    }


class BattleSnapshotSerializer:
    def build_snapshot(
        self,
        battle: AbstractBattle,
        candidates: dict[str, CandidateAction],
        *,
        metadata: BattleRequestMetadata | None = None,
        criteria: dict[str, str] | None = None,
        recent_history: list[dict[str, Any]] | None = None,
        beliefs: dict[str, Any] | None = None,
        consequences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if metadata is None:
            metadata = extract_request_metadata(
                battle,
                state_version=0,
            )
            battle_turn = getattr(battle, "turn", 0)
            if isinstance(battle_turn, int) and battle_turn:
                metadata = BattleRequestMetadata(
                    battle_id=metadata.battle_id,
                    request_id=metadata.request_id,
                    state_version=metadata.state_version,
                    turn=battle_turn,
                    request_type=metadata.request_type,
                    force_switch=metadata.force_switch,
                    wait=metadata.wait,
                    trapped=metadata.trapped,
                    maybe_trapped=metadata.maybe_trapped,
                    deadline_monotonic=metadata.deadline_monotonic,
                )

        criteria = criteria or {}
        recent_history = list(recent_history or [])[-5:]
        beliefs = beliefs if beliefs is not None else build_hidden_information_ledger(battle)
        consequences = consequences or {}

        self_active = _mon_view(
            getattr(battle, "active_pokemon", None), active=True, battle=battle
        )
        self_team_raw = getattr(battle, "team", {})
        self_team = [
            _mon_view(mon, active=mon is getattr(battle, "active_pokemon", None), battle=battle)
            for _, mon in sorted(self_team_raw.items(), key=lambda item: str(item[0]))
        ] if isinstance(self_team_raw, Mapping) else []

        opp_active = _mon_view(getattr(battle, "opponent_active_pokemon", None), active=True, battle=battle)
        opp_team_raw = getattr(battle, "opponent_team", {})
        revealed_mons = list(opp_team_raw.values()) if isinstance(opp_team_raw, Mapping) else []
        opp_team_slots = [_mon_view(mon) for mon in revealed_mons[:6]]
        while len(opp_team_slots) < 6:
            opp_team_slots.append(_mon_view(None, revealed=False))

        weather_names = _effect_names(getattr(battle, "weather", {}))
        fields = [
            name
            for field in getattr(battle, "fields", []) or []
            if (name := (_enum_name(field) or str(field)))
        ]

        legal_actions = []
        for cid in sorted(candidates):
            candidate = candidates[cid]
            legal_actions.append(
                {
                    "id": cid,
                    "kind": candidate.kind,
                    "label": candidate.label,
                    "facts": _json_safe(candidate.facts),
                }
            )

        return {
            "state_schema": 2,
            "battle_format": getattr(battle, "format", "gen9randombattle"),
            "turn": metadata.turn,
            "request": _request_view(metadata),
            "weather": weather_names[0] if weather_names else None,
            "fields": fields,
            "side_conditions": {
                "self": _condition_map(getattr(battle, "side_conditions", {})),
                "opponent": _condition_map(
                    getattr(battle, "opponent_side_conditions", {})
                ),
            },
            "can_tera": getattr(battle, "can_tera", False),
            "strategic_hypotheses": _hypotheses(metadata.turn),
            "glossary": {
                "switch": "Replace the active Pokemon with a legal bench Pokemon.",
                "setup": "A move that changes a future turn resource, boost, or field.",
                "status": "A persistent condition such as burn, paralysis, or sleep.",
                "hazard": "A field effect that can affect a later switch-in.",
                "priority": "An action-order modifier applied before speed ties.",
                "safe_action": "An action whose stated consequences are supported by evidence.",
                "risky_prediction": "A possible outcome with unresolved information.",
                "win_condition": "A position or resource pattern that can lead to victory.",
                "lose_condition": "A threat or resource loss that can lead to defeat.",
            },
            "history": _json_safe(recent_history),
            "criteria": _json_safe(criteria),
            "beliefs": _json_safe(beliefs),
            "opponent_responses": _json_safe(consequences),
            "self": {"active_pokemon": self_active, "team": self_team},
            "opponent": {
                "active_pokemon": opp_active,
                "team_slots": opp_team_slots,
            },
            "legal_actions": legal_actions,
        }
