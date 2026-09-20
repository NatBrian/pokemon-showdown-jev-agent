import re
from dataclasses import dataclass, field
from typing import Any

from poke_env.battle import AbstractBattle, Move, Pokemon
from poke_env.player.battle_order import (
    BattleOrder,
    DefaultBattleOrder,
    SingleBattleOrder,
)


@dataclass
class CandidateAction:
    id: str
    kind: str  # "move", "move_tera", "switch", "default"
    label: str
    order_ref: BattleOrder
    facts: dict[str, Any] = field(default_factory=dict)


def _sanitize_id(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "", text.lower().replace("-", "").replace(" ", ""))


def _unique_id(base: str, existing: dict[str, CandidateAction]) -> str:
    """Keep telemetry/action IDs unique even for duplicate protocol names."""
    if base not in existing:
        return base
    suffix = 2
    while f"{base}_{suffix}" in existing:
        suffix += 1
    return f"{base}_{suffix}"


def _enum_name(value: Any, default: str = "UNKNOWN") -> str:
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    if isinstance(value, str):
        return value
    return default


def _move_facts(move: Move, *, tera: bool = False) -> dict[str, Any]:
    facts = {
        "base_power": getattr(move, "base_power", 0),
        "type": _enum_name(getattr(move, "type", None)),
        "category": _enum_name(getattr(move, "category", None), "STATUS"),
        "accuracy": getattr(move, "accuracy", 100),
        "pp": getattr(move, "current_pp", None),
    }
    if tera:
        facts["tera"] = True
    return facts


def _switch_facts(pokemon: Pokemon) -> dict[str, Any]:
    status = getattr(pokemon, "status", None)
    return {
        "species": getattr(pokemon, "species", "pokemon"),
        "hp_fraction": getattr(pokemon, "current_hp_fraction", 1.0),
        "status": _enum_name(status, "HEALTHY") if status else "HEALTHY",
    }


def build_candidate_actions(battle: AbstractBattle) -> dict[str, CandidateAction]:
    """Build the complete legal registry from this request's legal orders.

    Candidate IDs and labels are presentation metadata. The exact order object
    is retained because it is the only object later submitted to Showdown.
    """
    candidates: dict[str, CandidateAction] = {}

    try:
        legal_orders = list(getattr(battle, "valid_orders", ()) or ())
    except TypeError:
        legal_orders = []

    for order in legal_orders:
        if isinstance(order, DefaultBattleOrder):
            cid = _unique_id("default", candidates)
            candidates[cid] = CandidateAction(
                id=cid,
                kind="default",
                label="Wait / default order",
                order_ref=order,
                facts={"default": True},
            )
            continue

        if not isinstance(order, SingleBattleOrder):
            cid = _unique_id("order", candidates)
            candidates[cid] = CandidateAction(
                id=cid,
                kind="default",
                label="Current legal order",
                order_ref=order,
                facts={},
            )
            continue

        underlying = order.order
        if isinstance(underlying, Move):
            move_name = getattr(underlying, "id", "move")
            clean_name = _sanitize_id(str(move_name)) or "move"
            is_tera = bool(getattr(order, "terastallize", False))
            base = f"move_{clean_name}"
            if is_tera:
                base += "_tera"
            cid = _unique_id(base, candidates)
            display_label = str(move_name).replace("_", " ").title()
            if is_tera:
                display_label += " (Terastallize)"
            candidates[cid] = CandidateAction(
                id=cid,
                kind="move_tera" if is_tera else "move",
                label=display_label,
                order_ref=order,
                facts=_move_facts(underlying, tera=is_tera),
            )
            continue

        if isinstance(underlying, Pokemon):
            species_name = getattr(underlying, "species", None) or getattr(
                underlying, "name", "pokemon"
            )
            clean_species = _sanitize_id(str(species_name)) or "pokemon"
            cid = _unique_id(f"switch_{clean_species}", candidates)
            candidates[cid] = CandidateAction(
                id=cid,
                kind="switch",
                label=f"Switch to {species_name}",
                order_ref=order,
                facts=_switch_facts(underlying),
            )
            continue

        cid = _unique_id("order", candidates)
        candidates[cid] = CandidateAction(
            id=cid,
            kind="default",
            label="Current legal order",
            order_ref=order,
            facts={},
        )

    return candidates
