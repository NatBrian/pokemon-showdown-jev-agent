from typing import Any
from poke_env.battle import AbstractBattle
from jev_showdown.battle.candidates import CandidateAction


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
    status = getattr(mon, "status", None)
    types = [getattr(getattr(mon, "type_1", None), "name", "")]
    if getattr(mon, "type_2", None):
        types.append(getattr(mon.type_2, "name", ""))
    return {
        "revealed": True,
        "species": getattr(mon, "species", "Unknown"),
        "hp_fraction": getattr(mon, "current_hp_fraction", 1.0),
        "hp": getattr(mon, "current_hp", None),
        "max_hp": getattr(mon, "max_hp", None),
        "level": getattr(mon, "level", None),
        "fainted": getattr(mon, "fainted", False),
        "status": getattr(status, "name", None) if status is not None else None,
        "types": types,
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

        return {
            "state_schema": 1,
            "battle_format": getattr(battle, "format", "gen9randombattle"),
            "turn": getattr(battle, "turn", 1),
            "weather": getattr(battle.weather, "name", None) if getattr(battle, "weather", None) else None,
            "fields": [getattr(f, "name", str(f)) for f in getattr(battle, "fields", [])],
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
