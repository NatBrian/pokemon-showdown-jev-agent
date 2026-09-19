from dataclasses import dataclass, field
from typing import Any

@dataclass
class TurnHistoryTracker:
    events: list[dict[str, Any]] = field(default_factory=list)

    def add_event(self, turn: int, actor: str, action: str, damage_pct: int | None = None, status: str | None = None, note: str | None = None):
        self.events.append({
            "turn": turn,
            "actor": actor,
            "action": action,
            "damage_pct": damage_pct,
            "status": status,
            "note": note
        })

    def get_recent_events(self, limit: int = 5) -> list[dict[str, Any]]:
        return self.events[-limit:]
