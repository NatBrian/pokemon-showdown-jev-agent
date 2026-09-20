from typing import Any
from poke_env.battle import AbstractBattle
from jev_showdown.battle.candidates import CandidateAction


def _enum_name(value: Any) -> str | None:
    raw = getattr(value, "name", value)
    if isinstance(raw, str):
        return raw
    return None


def _condition_map(values: Any) -> dict[str, Any]:
    if not isinstance(values, dict):
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
    if isinstance(values, dict):
        values = list(values.keys())
    if not isinstance(values, (list, set, tuple)):
        return []
    return [name for value in values if (name := (_enum_name(value) or str(value)))]


def _mon_view(mon: Any, *, revealed: bool = True) -> dict[str, Any]:
    """Serialize a poke_env Pokemon into the snapshot schema."""
    if mon is None or not revealed:
        return {
            "revealed": revealed,
            "species": None,
            "hp_fraction": 1.0,
            "hp": None,
            "max_hp": None,
            "level": None,
            "fainted": False,
            "status": None,
        }
    status = _enum_name(getattr(mon, "status", None))
    types = []
    for type_value in (getattr(mon, "type_1", None), getattr(mon, "type_2", None)):
        type_name = _enum_name(type_value)
        if type_name:
            types.append(type_name)
    return {
        "revealed": True,
        "species": str(getattr(mon, "species", "Unknown")),
        "hp_fraction": getattr(mon, "current_hp_fraction", 1.0),
        "hp": getattr(mon, "current_hp", None),
        "max_hp": getattr(mon, "max_hp", None),
        "level": getattr(mon, "level", None),
        "fainted": getattr(mon, "fainted", False),
        "status": status,
        "types": types,
        "boosts": _condition_map(getattr(mon, "boosts", {})),
        "effects": _effect_names(getattr(mon, "effects", set())),
    }


class BattleSnapshotSerializer:
    def build_snapshot(self, battle: AbstractBattle, candidates: dict[str, CandidateAction]) -> dict[str, Any]:
        # Active Self
        self_active = _mon_view(getattr(battle, "active_pokemon", None))

        # Self Team (6 known)
        self_team = [_mon_view(mon) for mon in getattr(battle, "team", {}).values()]

        # Active Opponent
        opp_active = _mon_view(getattr(battle, "opponent_active_pokemon", None))

        # Opponent Team Fog of War: 6 slots total
        # Fill revealed species from battle.opponent_team, rest as unrevealed slots
        opp_team_slots = []
        revealed_mons = list(getattr(battle, "opponent_team", {}).values())
        for mon in revealed_mons[:6]:
            opp_team_slots.append(_mon_view(mon))
        while len(opp_team_slots) < 6:
            # Unrevealed Poké Ball: capacity slot, nothing is guessed.
            opp_team_slots.append(_mon_view(None, revealed=False))

        weather_names = _effect_names(getattr(battle, "weather", {}))

        return {
            "state_schema": 1,
            "battle_format": getattr(battle, "format", "gen9randombattle"),
            "turn": getattr(battle, "turn", 1),
            "weather": weather_names[0] if weather_names else None,
            "fields": [
                name
                for field in getattr(battle, "fields", [])
                if (name := (_enum_name(field) or str(field)))
            ],
            "side_conditions": {
                "self": _condition_map(getattr(battle, "side_conditions", {})),
                "opponent": _condition_map(
                    getattr(battle, "opponent_side_conditions", {})
                ),
            },
            "can_tera": getattr(battle, "can_tera", False),
            "self": {
                "active_pokemon": self_active,
                "team": self_team
            },
            "opponent": {
                "active_pokemon": opp_active,
                "team_slots": opp_team_slots
            },
            "legal_actions": [
                {
                    "id": cid,
                    "kind": cand.kind,
                    "label": cand.label,
                    "facts": cand.facts
                }
                for cid, cand in candidates.items()
            ]
        }
