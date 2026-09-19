from typing import Any
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

            # Simple bounded heuristic damage estimation % range
            # Base power * multiplier * STAB factor (~1.2-1.5) scaled to %
            approx_damage = int((base_power * mult * 0.4) * (1.5 if cand.kind == "move_tera" else 1.0))
            damage_min = max(0, int(approx_damage * 0.85))
            damage_max = max(0, int(approx_damage * 1.0))
            cand.facts["estimated_damage_range"] = [damage_min, damage_max]
            cand.facts["estimated_ko"] = (damage_min >= int(opp_hp * 100))

            crit_desc = f"{cand.label}; Power: {base_power}, Type: {m_type}, {mult}x effective. Est Damage: {damage_min}-{damage_max}%"
            if cand.facts["estimated_ko"]:
                crit_desc += " [Likely KO]"
            criteria[cid] = crit_desc
        elif cand.kind == "switch":
            hp_pct = int(cand.facts.get("hp_fraction", 1.0) * 100)
            status = cand.facts.get("status", "HEALTHY")
            crit_desc = f"{cand.label}; HP: {hp_pct}%, Status: {status}."
            criteria[cid] = crit_desc

    return criteria
