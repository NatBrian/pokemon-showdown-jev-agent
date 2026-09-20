"""Bounded action-response summaries; this module never chooses an action."""

from collections.abc import Mapping
from typing import Any

from poke_env.battle import AbstractBattle

from jev_showdown.battle.beliefs import build_hidden_information_ledger
from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.battle.contracts import Fact


def _fact(
    value: Any,
    source: str = "unknown",
    unit: str = "response_category",
    assumptions: tuple[str, ...] = (),
) -> dict[str, Any]:
    result = Fact(
        value=value,
        source=source,  # type: ignore[arg-type]
        unit=unit,
        assumptions=assumptions,
    ).to_dict()
    result["probability"] = None
    return result


def _species_values(beliefs: Mapping[str, Any], visibility: set[str]) -> list[str]:
    values: list[str] = []
    for slot in beliefs.get("opponent_slots", []):
        if slot.get("visibility") not in visibility:
            continue
        species = slot.get("species", {})
        value = species.get("value") if isinstance(species, Mapping) else None
        if isinstance(value, str):
            values.append(value)
    return values


def _known_moves(beliefs: Mapping[str, Any]) -> list[str]:
    moves: list[str] = []
    for slot in beliefs.get("opponent_slots", []):
        if slot.get("visibility") != "revealed_active":
            continue
        for move in slot.get("moves", []):
            value = move.get("value") if isinstance(move, Mapping) else None
            if isinstance(value, str):
                moves.append(value)
    return moves


def _switch_in(candidate: CandidateAction) -> dict[str, Any]:
    species = candidate.facts.get("species")
    hp_fraction = candidate.facts.get("hp_fraction")
    return {
        "species": _fact(species, "observed", "species_id") if species else _fact(None, assumptions=("switch target is unavailable",)),
        "hp_fraction": _fact(hp_fraction, "observed", "fraction_of_max_hp") if isinstance(hp_fraction, (int, float)) else _fact(None, assumptions=("switch HP is unavailable",)),
        "entry_hazard_damage": _fact(
            None,
            assumptions=("entry hazards and exact switch-in mechanics are not verified here",),
        ),
    }


def compile_action_responses(
    battle: AbstractBattle,
    candidates: dict[str, CandidateAction],
    beliefs: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Compile possible response buckets while retaining unknown probability."""
    del battle  # The current compiler intentionally relies on the canonical beliefs ledger.
    revealed_species = _species_values(beliefs, {"revealed_bench", "fainted"})
    known_moves = _known_moves(beliefs)
    responses: dict[str, dict[str, Any]] = {}

    for action_id, candidate in candidates.items():
        response = {
            "action_id": action_id,
            "opponent_stays": _fact(
                None,
                assumptions=("opponent response is not predicted",),
            ),
            "opponent_uses_known_move": _fact(
                known_moves or None,
                "observed" if known_moves else "unknown",
                "move_id_list",
                ("only revealed moves are listed",),
            ),
            "opponent_uses_unknown_move": _fact(
                None,
                assumptions=("unrevealed opponent moves remain possible",),
            ),
            "opponent_sets_up_or_statuses": _fact(
                None,
                assumptions=("setup and status response is not predicted",),
            ),
            "opponent_switches_revealed": _fact(
                revealed_species or None,
                "observed" if revealed_species else "unknown",
                "species_id_list",
                ("revealed species are listed without a switch probability",),
            ),
            "opponent_switches_unknown": _fact(
                None,
                assumptions=("unrevealed opponent slots remain possible",),
            ),
        }

        if candidate.kind == "switch":
            response["switch_in"] = _switch_in(candidate)
            response["double_switch"] = {
                "our_switch": {
                    "action_id": action_id,
                    "target_species": candidate.facts.get("species"),
                    "consequence": response["switch_in"],
                },
                "opponent_switch": {
                    "revealed": response["opponent_switches_revealed"],
                    "unknown": response["opponent_switches_unknown"],
                },
            }
        else:
            response["action_consequence"] = candidate.facts.get(
                "damage",
                _fact(None, assumptions=("move consequence is unavailable",)),
            )

        responses[action_id] = response

    return responses
