from dataclasses import dataclass
from poke_env.player.battle_order import BattleOrder

@dataclass(frozen=True)
class ValidatedOrder:
    order: BattleOrder
    is_fallback: bool
    fallback_reason: str | None
    chosen_id: str
