from typing import Any
from poke_env.battle import AbstractBattle
from poke_env.player.battle_order import BattleOrder, DefaultBattleOrder
from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.battle.validator import ValidatedOrder
from jev_showdown.decision.protocol import JevDecisionResponse

def select_deterministic_fallback(candidates: dict[str, CandidateAction], battle: AbstractBattle, reason: str) -> ValidatedOrder:
    if not candidates:
        # Candidate enumeration can be empty while poke-env still exposes a
        # legal order (for example during a forced request transition). Use
        # that order before falling back to poke-env's protocol-safe default.
        try:
            legal_orders = getattr(battle, "valid_orders", None)
            legal_order = next(iter(legal_orders), None) if legal_orders else None
        except Exception:
            legal_order = None
        if legal_order is not None:
            return ValidatedOrder(
                order=legal_order,
                is_fallback=True,
                fallback_reason=reason,
                chosen_id="legal_order_0",
            )
        return ValidatedOrder(
            order=DefaultBattleOrder(),
            is_fallback=True,
            fallback_reason=reason,
            chosen_id="emergency_default",
        )

    # Priority 1: Legal forced single action
    if len(candidates) == 1:
        single_id = next(iter(candidates))
        return ValidatedOrder(order=candidates[single_id].order_ref, is_fallback=True, fallback_reason=f"{reason} (Forced action)", chosen_id=single_id)

    # Priority 2: Safe legal move with highest expected damage / power
    best_move_id = None
    best_score = -1.0
    for cid, cand in candidates.items():
        if cand.kind in ("move", "move_tera"):
            bp = cand.facts.get("base_power", 0)
            mult = cand.facts.get("type_multiplier", 1.0)
            if isinstance(mult, dict):
                mult = mult.get("value", 1.0)
            if not isinstance(mult, (int, float)):
                mult = 1.0
            score = bp * mult
            if score > best_score:
                best_score = score
                best_move_id = cid

    if best_move_id:
        return ValidatedOrder(order=candidates[best_move_id].order_ref, is_fallback=True, fallback_reason=f"{reason} (Best damage heuristic)", chosen_id=best_move_id)

    # Priority 3: First available legal switch or action
    first_id = next(iter(candidates))
    return ValidatedOrder(order=candidates[first_id].order_ref, is_fallback=True, fallback_reason=f"{reason} (First legal candidate)", chosen_id=first_id)

def resolve_order(
    jev_res: JevDecisionResponse,
    candidates: dict[str, CandidateAction],
    battle: AbstractBattle
) -> ValidatedOrder:
    if jev_res.error:
        return select_deterministic_fallback(candidates, battle, f"Jev error: {jev_res.error}")

    choice = jev_res.choice
    if not choice or choice not in candidates:
        return select_deterministic_fallback(candidates, battle, f"Invalid choice '{choice}' not in legal candidates")

    return ValidatedOrder(
        order=candidates[choice].order_ref,
        is_fallback=False,
        fallback_reason=None,
        chosen_id=choice
    )
