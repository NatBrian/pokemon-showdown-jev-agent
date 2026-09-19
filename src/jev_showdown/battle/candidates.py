import re
from dataclasses import dataclass, field
from typing import Any
from poke_env.battle import AbstractBattle
from poke_env.player.battle_order import BattleOrder, SingleBattleOrder

@dataclass
class CandidateAction:
    id: str
    kind: str  # "move", "move_tera", "switch"
    label: str
    order_ref: BattleOrder
    facts: dict[str, Any] = field(default_factory=dict)

def _sanitize_id(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "", text.lower().replace("-", "").replace(" ", ""))

def build_candidate_actions(battle: AbstractBattle) -> dict[str, CandidateAction]:
    candidates: dict[str, CandidateAction] = {}
    
    # 1. Available Moves
    for move in battle.available_moves:
        if getattr(move, "current_pp", 1) <= 0:
            continue
        move_name = getattr(move, "id", str(move))
        clean_name = _sanitize_id(move_name)
        cid = f"move_{clean_name}"
        display_label = getattr(move, "id", clean_name).replace("_", " ").title()
        
        candidates[cid] = CandidateAction(
            id=cid,
            kind="move",
            label=display_label,
            order_ref=SingleBattleOrder(move),
            facts={
                "base_power": getattr(move, "base_power", 0),
                "type": getattr(move.type, "name", "UNKNOWN") if getattr(move, "type", None) else "UNKNOWN",
                "category": getattr(move.category, "name", "STATUS") if getattr(move, "category", None) else "STATUS",
                "accuracy": getattr(move, "accuracy", 100),
            }
        )
        
        # Tera variant if Terastallization is available
        if getattr(battle, "can_tera", False):
            tera_cid = f"move_{clean_name}_tera"
            candidates[tera_cid] = CandidateAction(
                id=tera_cid,
                kind="move_tera",
                label=f"{display_label} (Terastallize)",
                order_ref=SingleBattleOrder(move, terastallize=True),
                facts={
                    "base_power": getattr(move, "base_power", 0),
                    "type": getattr(move.type, "name", "UNKNOWN") if getattr(move, "type", None) else "UNKNOWN",
                    "category": getattr(move.category, "name", "STATUS") if getattr(move, "category", None) else "STATUS",
                    "accuracy": getattr(move, "accuracy", 100),
                    "tera": True,
                }
            )

    # 2. Available Switches
    for mon in battle.available_switches:
        species_name = getattr(mon, "species", "pokemon")
        clean_species = _sanitize_id(species_name)
        cid = f"switch_{clean_species}"
        hp_frac = getattr(mon, "current_hp_fraction", 1.0)
        
        candidates[cid] = CandidateAction(
            id=cid,
            kind="switch",
            label=f"Switch to {species_name}",
            order_ref=SingleBattleOrder(mon),
            facts={
                "species": species_name,
                "hp_fraction": hp_frac,
                "status": getattr(mon.status, "name", "HEALTHY") if getattr(mon, "status", None) else "HEALTHY",
            }
        )
        
    return candidates
