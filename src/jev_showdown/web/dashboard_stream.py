"""Thread-safe normalized dashboard state delivery over the live WebSocket."""
from __future__ import annotations

from threading import RLock
from typing import Any, Mapping

from jev_showdown.web.dashboard_state import DashboardProjector


class DashboardEventStream:
    """Own the dashboard projection while preserving raw protocol messages."""

    STATE_EVENT_TYPES = frozenset(
        {
            "EVALUATION_SETUP",
            "STATUS_UPDATE",
            "BATTLE_START",
            "TURN_DECISION",
            "BATTLE_END",
            "TELEMETRY_ERROR",
        }
    )

    def __init__(self, projector: DashboardProjector | None = None) -> None:
        self.projector = projector or DashboardProjector()
        self._lock = RLock()

    def publish(self, event: Mapping[str, Any]) -> dict[str, Any] | None:
        """Apply a state-bearing event and return its browser envelope."""
        event_type = event.get("type")
        if event_type not in self.STATE_EVENT_TYPES:
            return None
        with self._lock:
            self.projector.apply_event(event)
            state = self.projector.snapshot()
            state["kind"] = "event"
            return {
                "type": "DASHBOARD_STATE",
                "event_type": event_type,
                "state": state,
            }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self.projector.snapshot()

    def snapshot_message(self) -> dict[str, Any]:
        return {
            "type": "DASHBOARD_STATE",
            "event_type": None,
            "state": self.snapshot(),
        }
