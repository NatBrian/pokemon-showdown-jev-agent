from typing import Any

from poke_env.calc.damage_calc_gen9 import calculate_damage
from poke_env.player.battle_order import SingleBattleOrder
from poke_env.battle import AbstractBattle
from jev_showdown.battle.candidates import CandidateAction

# Standard Gen 9 Type Chart multipliers
TYPE_CHART = {
    "NORMAL": {"ROCK": 0.5, "GHOST": 0.0, "STEEL": 0.5},
    "FIRE": {"FIRE": 0.5, "WATER": 0.5, "GRASS": 2.0, "ICE": 2.0, "BUG": 2.0, "ROCK": 0.5, "DRAGON": 0.5, "STEEL": 2.0},
    "WATER": {"FIRE": 2.0, "WATER": 0.5, "GRASS": 0.5, "GROUND": 2.0, "ROCK": 2.0, "DRAGON": 0.5},
    "ELECTRIC": {"WATER": 2.0, "ELECTRIC": 0.5, "GRASS": 0.5, "GROUND": 0.0, "FLYING": 2.0, "DRAGON": 0.5},
    "GRASS": {"FIRE": 0.5, "WATER": 2.0, "GRASS": 0.5, "POISON": 0.5, "GROUND": 2.0, "FLYING": 0.5, "BUG": 0.5, "ROCK": 2.0, "DRAGON": 0.5, "STEEL": 0.5},
    "ICE": {"FIRE": 0.5, "WATER": 0.5, "GRASS": 2.0, "ICE": 0.5, "GROUND": 2.0, "FLYING": 2.0, "DRAGON": 2.0, "STEEL": 0.5},
    "FIGHTING": {"NORMAL": 2.0, "ICE": 2.0, "POISON": 0.5, "FLYING": 0.5, "PSYCHIC": 0.5, "BUG": 0.5, "ROCK": 2.0, "GHOST": 0.0, "DARK": 2.0, "STEEL": 2.0, "FAIRY": 0.5},
    "POISON": {"GRASS": 2.0, "POISON": 0.5, "GROUND": 0.5, "ROCK": 0.5, "GHOST": 0.5, "STEEL": 0.0, "FAIRY": 2.0},
    "GROUND": {"FIRE": 2.0, "ELECTRIC": 2.0, "GRASS": 0.5, "POISON": 2.0, "FLYING": 0.0, "BUG": 0.5, "ROCK": 2.0, "STEEL": 2.0},
    "FLYING": {"ELECTRIC": 0.5, "GRASS": 2.0, "FIGHTING": 2.0, "BUG": 2.0, "ROCK": 0.5, "STEEL": 0.5},
    "PSYCHIC": {"FIGHTING": 2.0, "POISON": 2.0, "PSYCHIC": 0.5, "DARK": 0.0, "STEEL": 0.5},
    "BUG": {"FIRE": 0.5, "GRASS": 2.0, "FIGHTING": 0.5, "POISON": 0.5, "FLYING": 0.5, "PSYCHIC": 2.0, "GHOST": 0.5, "DARK": 2.0, "STEEL": 0.5, "FAIRY": 0.5},
    "ROCK": {"FIRE": 2.0, "ICE": 2.0, "FIGHTING": 0.5, "GROUND": 0.5, "FLYING": 2.0, "BUG": 2.0, "STEEL": 0.5},
    "GHOST": {"NORMAL": 0.0, "PSYCHIC": 2.0, "GHOST": 2.0, "DARK": 0.5},
    "DRAGON": {"DRAGON": 2.0, "STEEL": 0.5, "FAIRY": 0.0},
    "DARK": {"FIGHTING": 0.5, "PSYCHIC": 2.0, "GHOST": 2.0, "DARK": 0.5, "FAIRY": 0.5},
    "STEEL": {"FIRE": 0.5, "WATER": 0.5, "ELECTRIC": 0.5, "ICE": 2.0, "ROCK": 2.0, "STEEL": 0.5, "FAIRY": 2.0},
    "FAIRY": {"FIRE": 0.5, "FIGHTING": 2.0, "POISON": 0.5, "DRAGON": 2.0, "DARK": 2.0, "STEEL": 0.5}
}

def calculate_type_multiplier(attack_type: str, def_type_1: str | None, def_type_2: str | None) -> float:
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
    """Return a poke-env Gen 9 damage range when all required state exists.

    Random Battles expose incomplete opponent information, and the calculator
    asserts when stats or identifiers are unavailable. Those cases are
    intentionally returned as ``None`` so the caller can use a visibly
    labeled heuristic estimate instead of pretending the result is exact.
    Terastallize variants stay on the estimate path because the calculator's
    battle object must be updated with the post-Tera attacker state first.
    """
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

def annotate_candidates_with_facts(battle: AbstractBattle, candidates: dict[str, CandidateAction]) -> dict[str, str]:
    criteria: dict[str, str] = {}
    opp = getattr(battle, "opponent_active_pokemon", None)
    opp_t1 = getattr(opp.type_1, "name", None) if opp and getattr(opp, "type_1", None) else None
    opp_t2 = getattr(opp.type_2, "name", None) if opp and getattr(opp, "type_2", None) else None
    opp_hp = getattr(opp, "current_hp_fraction", 1.0) if opp else 1.0

    for cid, cand in candidates.items():
        if cand.kind in ("move", "move_tera"):
            m_type = cand.facts.get("type", "UNKNOWN")
            base_power = cand.facts.get("base_power", 0)
            mult = calculate_type_multiplier(m_type, opp_t1, opp_t2)
            cand.facts["type_multiplier"] = mult

            exact_range = _exact_damage_percent(battle, cand, opp)
            if exact_range is not None:
                damage_min, damage_max = exact_range
                cand.facts["calculation_mode"] = "poke_env_gen9"
                cand.facts["calculation_assumptions"] = [
                    "poke-env Gen 9 calculator",
                    "current known battle stats and effects",
                ]
            else:
                # Bounded estimate for incomplete-information Random Battle
                # states. This is deliberately not called exact damage.
                approx_damage = int(
                    (base_power * mult * 0.4)
                    * (1.5 if cand.kind == "move_tera" else 1.0)
                )
                damage_min = max(0, int(approx_damage * 0.85))
                damage_max = max(0, int(approx_damage * 1.0))
                cand.facts["calculation_mode"] = "heuristic_estimate"
                cand.facts["calculation_assumptions"] = [
                    "base power and type effectiveness",
                    "approximate damage scaling",
                    "unknown sets, items, abilities, and exact stats",
                ]
            cand.facts["estimated_damage_range"] = [damage_min, damage_max]
            cand.facts["estimated_ko"] = (damage_min >= int(opp_hp * 100))

            damage_label = "Calc Damage" if cand.facts["calculation_mode"] == "poke_env_gen9" else "Est Damage"
            crit_desc = f"{cand.label}; Power: {base_power}, Type: {m_type}, {mult}x effective. {damage_label}: {damage_min}-{damage_max}%"
            if cand.facts["estimated_ko"]:
                crit_desc += " [Likely KO]"
            criteria[cid] = crit_desc
        elif cand.kind == "switch":
            hp_pct = int(cand.facts.get("hp_fraction", 1.0) * 100)
            status = cand.facts.get("status", "HEALTHY")
            crit_desc = f"{cand.label}; HP: {hp_pct}%, Status: {status}."
            criteria[cid] = crit_desc

    return criteria
