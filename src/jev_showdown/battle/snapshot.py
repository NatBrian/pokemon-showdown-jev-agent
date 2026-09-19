from typing import Any
from poke_env.battle import AbstractBattle
from jev_showdown.battle.candidates import CandidateAction

class BattleSnapshotSerializer:
    def build_snapshot(self, battle: AbstractBattle, candidates: dict[str, CandidateAction]) -> dict[str, Any]:
        # Active Self
        active_mon = getattr(battle, "active_pokemon", None)
        self_active = {
            "species": getattr(active_mon, "species", "Unknown"),
            "hp_fraction": getattr(active_mon, "current_hp_fraction", 1.0),
            "status": getattr(active_mon.status, "name", None) if active_mon and getattr(active_mon, "status", None) else None,
            "types": [getattr(active_mon.type_1, "name", "")] + ([getattr(active_mon.type_2, "name", "")] if getattr(active_mon, "type_2", None) else []) if active_mon else [],
        }
        
        # Self Team (6 known)
        self_team = []
        for mon in getattr(battle, "team", {}).values():
            self_team.append({
                "species": getattr(mon, "species", "Unknown"),
                "hp_fraction": getattr(mon, "current_hp_fraction", 1.0),
                "fainted": getattr(mon, "fainted", False),
                "status": getattr(mon.status, "name", None) if getattr(mon, "status", None) else None,
            })
            
        # Active Opponent
        opp_mon = getattr(battle, "opponent_active_pokemon", None)
        opp_active = {
            "species": getattr(opp_mon, "species", "Unknown") if opp_mon else "Unknown",
            "hp_fraction": getattr(opp_mon, "current_hp_fraction", 1.0) if opp_mon else 1.0,
            "status": getattr(opp_mon.status, "name", None) if opp_mon and getattr(opp_mon, "status", None) else None,
            "types": [getattr(opp_mon.type_1, "name", "")] + ([getattr(opp_mon.type_2, "name", "")] if getattr(opp_mon, "type_2", None) else []) if opp_mon else [],
        }
        
        # Opponent Team Fog of War: 6 slots total
        # Fill revealed species from battle.opponent_team, rest as unrevealed slots
        opp_team_slots = []
        revealed_mons = list(getattr(battle, "opponent_team", {}).values())
        for mon in revealed_mons[:6]:
            opp_team_slots.append({
                "revealed": True,
                "species": getattr(mon, "species", "Unknown"),
                "hp_fraction": getattr(mon, "current_hp_fraction", 1.0),
                "fainted": getattr(mon, "fainted", False),
                "status": getattr(mon.status, "name", None) if getattr(mon, "status", None) else None,
            })
        while len(opp_team_slots) < 6:
            opp_team_slots.append({
                "revealed": False,
                "species": None,
                "hp_fraction": 1.0,
                "fainted": False,
                "status": None
            })

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
