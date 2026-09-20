from collections.abc import Mapping
from typing import Any

from poke_env.battle import AbstractBattle
from poke_env.player.battle_order import BattleOrder, DefaultBattleOrder

from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.battle.contracts import DecisionFingerprint
from jev_showdown.battle.validator import ValidatedOrder
from jev_showdown.decision.protocol import JevDecisionResponse


def _fact_value(facts: Mapping[str, Any], key: str) -> Any:
    value = facts.get(key)
    return value.get("value") if isinstance(value, Mapping) else value


def _fact_is_trusted(facts: Mapping[str, Any], key: str, expected: Any) -> bool:
    value = facts.get(key)
    return (
        isinstance(value, Mapping)
        and value.get("value") == expected
        and value.get("source") in {"observed", "calculated"}
    )


def _guaranteed_exact_ko(candidate: CandidateAction) -> bool:
    facts = candidate.facts
    damage = facts.get("damage")
    target_state = facts.get("target_state")
    accuracy = facts.get("accuracy")
    if not isinstance(damage, Mapping) or damage.get("source") != "calculated":
        return False
    if damage.get("unit") != "percent_of_target_max_hp":
        return False
    if not _fact_is_trusted(facts, "ko", True):
        return False
    if not isinstance(target_state, Mapping) or target_state.get("source") not in {
        "observed",
        "calculated",
    }:
        return False
    if not isinstance(accuracy, (int, float)):
        return False
    return accuracy >= 1.0


def _continuation_value(candidate: CandidateAction) -> float | None:
    raw = candidate.facts.get("continuation_classification")
    if not isinstance(raw, Mapping) or raw.get("source") not in {
        "observed",
        "calculated",
    }:
        return None
    value = raw.get("value")
    return float(value) if isinstance(value, (int, float)) else None


def _first_legal_order(battle: AbstractBattle) -> BattleOrder | None:
    try:
        legal_orders = getattr(battle, "valid_orders", None)
        if legal_orders:
            return next(iter(legal_orders), None)
    except Exception:
        return None
    return None


def select_deterministic_fallback(
    candidates: dict[str, CandidateAction],
    battle: AbstractBattle,
    reason: str,
) -> ValidatedOrder:
    if not candidates:
        legal_order = _first_legal_order(battle)
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

    # 1. A single current legal order is already fully determined.
    if len(candidates) == 1:
        single_id = next(iter(candidates))
        return ValidatedOrder(
            order=candidates[single_id].order_ref,
            is_fallback=True,
            fallback_reason=f"{reason} (Forced action)",
            chosen_id=single_id,
        )

    # 2. Prefer an exact, guaranteed KO only when accuracy and target state are
    # represented as verified facts. Heuristic estimates never enter here.
    for cid, candidate in candidates.items():
        if _guaranteed_exact_ko(candidate):
            return ValidatedOrder(
                order=candidate.order_ref,
                is_fallback=True,
                fallback_reason=f"{reason} (Exact guaranteed KO)",
                chosen_id=cid,
            )

    # 3. Avoid an action marked as a verified immediate loss when another legal
    # action exists. If every action is marked as a loss, retain legality below.
    non_losses = [
        (cid, candidate)
        for cid, candidate in candidates.items()
        if not _fact_is_trusted(candidate.facts, "immediate_loss", True)
    ]
    if non_losses and len(non_losses) < len(candidates):
        cid, candidate = non_losses[0]
        return ValidatedOrder(
            order=candidate.order_ref,
            is_fallback=True,
            fallback_reason=f"{reason} (Avoided verified immediate loss)",
            chosen_id=cid,
        )

    # 4. Preserve a resource explicitly marked as the only known answer.
    for key in ("preserve_only_check", "only_known_answer"):
        for cid, candidate in candidates.items():
            if _fact_is_trusted(candidate.facts, key, True):
                return ValidatedOrder(
                    order=candidate.order_ref,
                    is_fallback=True,
                    fallback_reason=f"{reason} (Preserved only known check)",
                    chosen_id=cid,
                )

    # 5. Use a verified continuation classification, if one exists.
    ranked = [
        (score, cid, candidate)
        for cid, candidate in candidates.items()
        if (score := _continuation_value(candidate)) is not None
    ]
    if ranked:
        _, cid, candidate = max(ranked, key=lambda item: item[0])
        return ValidatedOrder(
            order=candidate.order_ref,
            is_fallback=True,
            fallback_reason=f"{reason} (Verified continuation)",
            chosen_id=cid,
        )

    # 6. No trustworthy ranking is available. Preserve the current registry
    # order instead of letting a heuristic number dominate the decision.
    first_id = next(iter(candidates))
    return ValidatedOrder(
        order=candidates[first_id].order_ref,
        is_fallback=True,
        fallback_reason=f"{reason} (First legal candidate)",
        chosen_id=first_id,
    )


def resolve_order(
    jev_res: JevDecisionResponse,
    candidates: dict[str, CandidateAction],
    battle: AbstractBattle,
    *,
    expected_fingerprint: DecisionFingerprint | None = None,
    current_fingerprint: DecisionFingerprint | None = None,
) -> ValidatedOrder:
    if (
        expected_fingerprint is not None
        and current_fingerprint is not None
        and expected_fingerprint != current_fingerprint
    ):
        return select_deterministic_fallback(
            candidates,
            battle,
            "Stale Jev response: decision fingerprint changed",
        )

    if jev_res.error:
        return select_deterministic_fallback(
            candidates, battle, f"Jev error: {jev_res.error}"
        )

    choice = jev_res.choice
    if not choice or choice not in candidates:
        return select_deterministic_fallback(
            candidates,
            battle,
            f"Invalid choice '{choice}' not in legal candidates",
        )

    return ValidatedOrder(
        order=candidates[choice].order_ref,
        is_fallback=False,
        fallback_reason=None,
        chosen_id=choice,
    )
