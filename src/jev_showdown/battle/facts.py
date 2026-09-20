from typing import Any

from poke_env.battle import AbstractBattle
from poke_env.calc.damage_calc_gen9 import calculate_damage
from poke_env.player.battle_order import SingleBattleOrder

from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.battle.contracts import Fact


# Standard Gen 9 type chart multipliers used only for the verified type fact.
TYPE_CHART = {
    "NORMAL": {"ROCK": 0.5, "GHOST": 0.0, "STEEL": 0.5},
    "FIRE": {
        "FIRE": 0.5,
        "WATER": 0.5,
        "GRASS": 2.0,
        "ICE": 2.0,
        "BUG": 2.0,
        "ROCK": 0.5,
        "DRAGON": 0.5,
        "STEEL": 2.0,
    },
    "WATER": {
        "FIRE": 2.0,
        "WATER": 0.5,
        "GRASS": 0.5,
        "GROUND": 2.0,
        "ROCK": 2.0,
        "DRAGON": 0.5,
    },
    "ELECTRIC": {
        "WATER": 2.0,
        "ELECTRIC": 0.5,
        "GRASS": 0.5,
        "GROUND": 0.0,
        "FLYING": 2.0,
        "DRAGON": 0.5,
    },
    "GRASS": {
        "FIRE": 0.5,
        "WATER": 2.0,
        "GRASS": 0.5,
        "POISON": 0.5,
        "GROUND": 2.0,
        "FLYING": 0.5,
        "BUG": 0.5,
        "ROCK": 2.0,
        "DRAGON": 0.5,
        "STEEL": 0.5,
    },
    "ICE": {
        "FIRE": 0.5,
        "WATER": 0.5,
        "GRASS": 2.0,
        "ICE": 0.5,
        "GROUND": 2.0,
        "FLYING": 2.0,
        "DRAGON": 2.0,
        "STEEL": 0.5,
    },
    "FIGHTING": {
        "NORMAL": 2.0,
        "ICE": 2.0,
        "POISON": 0.5,
        "FLYING": 0.5,
        "PSYCHIC": 0.5,
        "BUG": 0.5,
        "ROCK": 2.0,
        "GHOST": 0.0,
        "DARK": 2.0,
        "STEEL": 2.0,
        "FAIRY": 0.5,
    },
    "POISON": {
        "GRASS": 2.0,
        "POISON": 0.5,
        "GROUND": 0.5,
        "ROCK": 0.5,
        "GHOST": 0.5,
        "STEEL": 0.0,
        "FAIRY": 2.0,
    },
    "GROUND": {
        "FIRE": 2.0,
        "ELECTRIC": 2.0,
        "GRASS": 0.5,
        "POISON": 2.0,
        "FLYING": 0.0,
        "BUG": 0.5,
        "ROCK": 2.0,
        "STEEL": 2.0,
    },
    "FLYING": {
        "ELECTRIC": 0.5,
        "GRASS": 2.0,
        "FIGHTING": 2.0,
        "BUG": 2.0,
        "ROCK": 0.5,
        "STEEL": 0.5,
    },
    "PSYCHIC": {
        "FIGHTING": 2.0,
        "POISON": 2.0,
        "PSYCHIC": 0.5,
        "DARK": 0.0,
        "STEEL": 0.5,
    },
    "BUG": {
        "FIRE": 0.5,
        "GRASS": 2.0,
        "FIGHTING": 0.5,
        "POISON": 0.5,
        "FLYING": 0.5,
        "PSYCHIC": 2.0,
        "GHOST": 0.5,
        "DARK": 2.0,
        "STEEL": 0.5,
        "FAIRY": 0.5,
    },
    "ROCK": {
        "FIRE": 2.0,
        "ICE": 2.0,
        "FIGHTING": 0.5,
        "GROUND": 0.5,
        "FLYING": 2.0,
        "BUG": 2.0,
        "STEEL": 0.5,
    },
    "GHOST": {"NORMAL": 0.0, "PSYCHIC": 2.0, "GHOST": 2.0, "DARK": 0.5},
    "DRAGON": {"DRAGON": 2.0, "STEEL": 0.5, "FAIRY": 0.0},
    "DARK": {
        "FIGHTING": 0.5,
        "PSYCHIC": 2.0,
        "GHOST": 2.0,
        "DARK": 0.5,
        "FAIRY": 0.5,
    },
    "STEEL": {
        "FIRE": 0.5,
        "WATER": 0.5,
        "ELECTRIC": 0.5,
        "ICE": 2.0,
        "ROCK": 2.0,
        "STEEL": 0.5,
        "FAIRY": 2.0,
    },
    "FAIRY": {
        "FIRE": 0.5,
        "FIGHTING": 2.0,
        "POISON": 0.5,
        "DRAGON": 2.0,
        "DARK": 2.0,
        "STEEL": 0.5,
    },
}


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


def calculate_type_multiplier(
    attack_type: str, def_type_1: str | None, def_type_2: str | None
) -> float:
    mult = 1.0
    att = attack_type.upper()
    if att in TYPE_CHART:
        if def_type_1 and def_type_1.upper() in TYPE_CHART[att]:
            mult *= TYPE_CHART[att][def_type_1.upper()]
        if def_type_2 and def_type_2.upper() in TYPE_CHART[att]:
            mult *= TYPE_CHART[att][def_type_2.upper()]
    return mult


def _exact_damage_percent(
    battle: AbstractBattle,
    candidate: Any,
    opponent: Any,
) -> list[int] | None:
    """Return a calculator range only when the full known state is usable."""
    if candidate.kind != "move" or not isinstance(candidate.order_ref, SingleBattleOrder):
        return None
    attacker = getattr(battle, "active_pokemon", None)
    attacker_identifier = getattr(attacker, "identifier", None)
    defender_identifier = getattr(opponent, "identifier", None)
    max_hp = getattr(opponent, "max_hp", None)
    move = getattr(candidate.order_ref, "order", None)
    if not isinstance(attacker_identifier, str) or not isinstance(defender_identifier, str):
        return None
    if not isinstance(max_hp, (int, float)) or max_hp <= 0 or move is None:
        return None
    try:
        minimum, maximum = calculate_damage(
            attacker_identifier,
            defender_identifier,
            move,
            battle,
        )
        if not all(isinstance(value, (int, float)) for value in (minimum, maximum)):
            return None
        return [
            max(0, round(float(minimum) / max_hp * 100)),
            max(0, round(float(maximum) / max_hp * 100)),
        ]
    except (AssertionError, AttributeError, KeyError, TypeError, ValueError):
        return None


def _type_name(value: Any) -> str | None:
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    if isinstance(value, str):
        return value
    return None


def _display_accuracy(value: Any) -> str:
    if isinstance(value, (int, float)):
        percent = value * 100 if 0 <= value <= 1 else value
        return str(int(percent)) if float(percent).is_integer() else str(percent)
    return "unknown"


def _display_number(value: Any) -> str:
    return str(value) if isinstance(value, (int, float)) else "unknown"


def annotate_candidates_with_facts(
    battle: AbstractBattle, candidates: dict[str, CandidateAction]
) -> dict[str, str]:
    criteria: dict[str, str] = {}
    opp = getattr(battle, "opponent_active_pokemon", None)
    if opp is None:
        opp_t1 = opp_t2 = None
        opp_hp = None
    else:
        opp_t1 = _type_name(getattr(opp, "type_1", None))
        opp_t2 = _type_name(getattr(opp, "type_2", None))
        opp_hp = getattr(opp, "current_hp_fraction", None)

    for cid, cand in candidates.items():
        if cand.kind in ("move", "move_tera"):
            move_type = cand.facts.get("type")
            m_type = move_type if isinstance(move_type, str) else None
            base_power = cand.facts.get("base_power", 0)
            type_multiplier = (
                calculate_type_multiplier(m_type, opp_t1, opp_t2)
                if m_type and (opp_t1 or opp_t2)
                else None
            )
            if type_multiplier is None:
                cand.facts["type_multiplier"] = _fact(
                    None,
                    "unknown",
                    "multiplier",
                    assumptions=("attacker or defender type is unavailable",),
                )
            else:
                cand.facts["type_multiplier"] = _fact(
                    type_multiplier,
                    "calculated",
                    "multiplier",
                    1.0,
                    ("Gen 9 type chart",),
                )

            order_move = getattr(cand.order_ref, "order", None)
            if "priority" not in cand.facts:
                priority = getattr(order_move, "priority", None)
                if isinstance(priority, (int, float)):
                    cand.facts["priority"] = priority

            exact_range = _exact_damage_percent(battle, cand, opp)
            if exact_range is not None:
                cand.facts["calculation_mode"] = "poke_env_gen9"
                assumptions = (
                    "poke-env Gen 9 calculator",
                    "current known battle stats and effects",
                )
                cand.facts["damage"] = _fact(
                    exact_range,
                    "calculated",
                    "percent_of_target_max_hp",
                    1.0,
                    assumptions,
                )
                if isinstance(opp_hp, (int, float)):
                    guaranteed_ko = exact_range[0] >= opp_hp * 100
                    cand.facts["ko"] = _fact(
                        guaranteed_ko,
                        "calculated",
                        "boolean",
                        1.0,
                        ("minimum damage is compared with current target HP",),
                    )
                else:
                    cand.facts["ko"] = _fact(
                        None,
                        "unknown",
                        "boolean",
                        assumptions=("current target HP is unavailable",),
                    )
                damage_min, damage_max = exact_range
                damage_text = (
                    f"calculated damage {damage_min}-{damage_max}% of target max HP"
                )
                ko_text = cand.facts["ko"]["value"]
            else:
                if not isinstance(base_power, (int, float)):
                    base_power = 0
                multiplier_value = type_multiplier if type_multiplier is not None else 1.0
                approx_score = int(
                    (base_power * multiplier_value * 0.4)
                    * (1.5 if cand.kind == "move_tera" else 1.0)
                )
                estimate = [max(0, int(approx_score * 0.85)), max(0, approx_score)]
                cand.facts["calculation_mode"] = "heuristic_estimate"
                assumptions = (
                    "base power and type effectiveness",
                    "approximate damage scaling",
                    "unknown sets, items, abilities, and exact stats",
                )
                cand.facts["utility_estimate"] = _fact(
                    estimate,
                    "inferred",
                    "heuristic_relative_score",
                    assumptions=assumptions,
                )
                cand.facts["damage"] = _fact(
                    None,
                    "unknown",
                    "percent_of_target_max_hp",
                    assumptions=("verified calculator inputs are incomplete",),
                )
                cand.facts["ko"] = _fact(
                    None,
                    "unknown",
                    "boolean",
                    assumptions=("heuristic estimates cannot establish a KO",),
                )
                damage_min, damage_max = estimate
                damage_text = (
                    f"heuristic relative estimate {damage_min}-{damage_max}; "
                    "damage=unknown"
                )
                ko_text = "unknown"

            multiplier_text = (
                f"{type_multiplier}x effective"
                if type_multiplier is not None
                else "type effectiveness unknown"
            )
            accuracy = _display_accuracy(cand.facts.get("accuracy"))
            pp = _display_number(cand.facts.get("pp"))
            priority = _display_number(cand.facts.get("priority", 0))
            criteria[cid] = (
                f"{cand.label}; legal action; Power: {base_power}, "
                f"{multiplier_text}; {damage_text}; KO={ko_text}; "
                f"accuracy={accuracy}%; PP={pp}; priority={priority}."
            )
        elif cand.kind == "switch":
            hp_fraction = cand.facts.get("hp_fraction")
            hp_pct = int(hp_fraction * 100) if isinstance(hp_fraction, (int, float)) else None
            status = cand.facts.get("status", "unknown")
            unknown_hazard = _fact(
                None,
                "unknown",
                "percent_of_max_hp",
                assumptions=("entry hazards and switch-in mechanics are not verified here",),
            )
            cand.facts.setdefault(
                "consequences",
                {
                    "entry_hazard_damage": unknown_hazard,
                    "opponent_coverage": _fact(
                        None,
                        "unknown",
                        "representation",
                        assumptions=("opponent coverage is not fully revealed",),
                    ),
                },
            )
            hp_text = f"{hp_pct}%" if hp_pct is not None else "unknown"
            criteria[cid] = (
                f"{cand.label}; legal switch; HP: {hp_text}, Status: {status}; "
                "entry hazard damage=unknown; opponent coverage=unknown."
            )

    return criteria
