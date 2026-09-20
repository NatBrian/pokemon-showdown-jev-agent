"""Conservative, evidence-labelled opponent information for Random Battles."""

from collections.abc import Mapping, Sequence
from typing import Any

from poke_env.battle import AbstractBattle

from jev_showdown.battle.contracts import Fact


def _fact(
    value: Any,
    source: str,
    unit: str | None = None,
    confidence: float | None = None,
    assumptions: tuple[str, ...] = (),
) -> dict[str, Any]:
    return Fact(
        value=value,
        source=source,  # type: ignore[arg-type]
        unit=unit,
        confidence=confidence,
        assumptions=assumptions,
    ).to_dict()


def _name(value: Any) -> str | None:
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    if isinstance(value, str):
        return value
    return None


def _observed(value: Any, unit: str) -> dict[str, Any]:
    return _fact(value, "observed", unit, 1.0)


def _unknown(unit: str, *assumptions: str) -> dict[str, Any]:
    return _fact(None, "unknown", unit, assumptions=tuple(assumptions))


def _move_facts(mon: Any) -> list[dict[str, Any]]:
    raw_moves = getattr(mon, "moves", ())
    if isinstance(raw_moves, Mapping):
        raw_moves = list(raw_moves.keys())
    if not isinstance(raw_moves, Sequence) or isinstance(raw_moves, (str, bytes)):
        raw_moves = ()

    result: list[dict[str, Any]] = []
    for move in raw_moves:
        move_id = _name(move) or getattr(move, "id", None)
        if isinstance(move_id, str):
            result.append(_observed(move_id, "move_id"))
    return result


def _slot(mon: Any, *, visibility: str, turn: int) -> dict[str, Any]:
    species = getattr(mon, "species", None) if mon is not None else None
    species_fact = (
        _observed(species, "species_id")
        if isinstance(species, str)
        else _unknown("species_id", "species has not been revealed")
    )
    forme = getattr(mon, "forme", None) if mon is not None else None
    status = _name(getattr(mon, "status", None)) if mon is not None else None
    if status is None and mon is not None:
        status = "HEALTHY"

    def observed_or_unknown(attribute: str, unit: str) -> dict[str, Any]:
        value = getattr(mon, attribute, None) if mon is not None else None
        return _observed(value, unit) if value is not None else _unknown(unit)

    boosts = getattr(mon, "boosts", None) if mon is not None else None
    effects = getattr(mon, "effects", None) if mon is not None else None
    boost_value = dict(boosts) if isinstance(boosts, Mapping) else None
    effect_value = sorted(_name(effect) or str(effect) for effect in effects) if isinstance(
        effects, (set, list, tuple)
    ) else None

    return {
        "visibility": visibility,
        "species": species_fact,
        "forme": _observed(forme, "forme_id") if forme else _unknown("forme_id"),
        "hp_fraction": observed_or_unknown("current_hp_fraction", "fraction_of_max_hp"),
        "hp": observed_or_unknown("current_hp", "hit_points"),
        "max_hp": observed_or_unknown("max_hp", "hit_points"),
        "status": _observed(status, "status") if status else _unknown("status"),
        "fainted": observed_or_unknown("fainted", "boolean"),
        "boosts": _observed(boost_value, "boost_stages") if boost_value is not None else _unknown("boost_stages"),
        "effects": _observed(effect_value, "effect_ids") if effect_value is not None else _unknown("effect_ids"),
        "moves": _move_facts(mon) if mon is not None else [],
        "item": observed_or_unknown("item", "item_id"),
        "ability": observed_or_unknown("ability", "ability_id"),
        "tera_type": observed_or_unknown("tera_type", "type_id"),
        "last_seen_turn": _observed(
            getattr(mon, "last_seen_turn", turn) if mon is not None else turn,
            "turn",
        ),
        "unrevealed_set_details": _unknown(
            "set_details",
            "moves, item, ability, EVs, and exact set are not fully revealed",
        ),
        "possible_hypotheses": [],
        "unknown_residual": _unknown(
            "representation",
            "no trusted Random Battle set predictor is connected",
        ),
    }


def build_hidden_information_ledger(battle: AbstractBattle) -> dict[str, Any]:
    """Return six opponent slots without guessing unrevealed team members."""
    active = getattr(battle, "opponent_active_pokemon", None)
    team = getattr(battle, "opponent_team", {})
    revealed = list(team.values()) if isinstance(team, Mapping) else []
    turn = getattr(battle, "turn", 0)
    turn = turn if isinstance(turn, int) and not isinstance(turn, bool) else 0

    ordered: list[tuple[Any, str]] = []
    if active is not None:
        ordered.append((active, "revealed_active"))
    for mon in revealed:
        if mon is active:
            continue
        visibility = "fainted" if getattr(mon, "fainted", False) else "revealed_bench"
        ordered.append((mon, visibility))
        if len(ordered) == 6:
            break

    slots = [_slot(mon, visibility=visibility, turn=turn) for mon, visibility in ordered[:6]]
    while len(slots) < 6:
        slots.append(_slot(None, visibility="unknown_slot", turn=turn))

    return {
        "format": getattr(battle, "format", "gen9randombattle"),
        "opponent_slots": slots,
        "possible_hypotheses": [],
        "unknown_residual": _unknown(
            "team_information",
            "unrevealed opponent species and sets are not observed",
        ),
    }
