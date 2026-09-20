"""Bounded raw Showdown protocol replay for dashboard renderers."""
from __future__ import annotations

from collections import deque
from typing import Any


class BattleFrameBuffer:
    """Keep a small, JSON-ready replay of the current battle's protocol."""

    def __init__(self, max_frames: int = 400) -> None:
        if max_frames < 1:
            raise ValueError("max_frames must be positive")
        self.max_frames = max_frames
        self._battle_tag: str | None = None
        self._frames: deque[list[str]] = deque(maxlen=max_frames)

    def start(self, battle_tag: str) -> None:
        self._battle_tag = battle_tag
        self._frames.clear()

    def append(self, battle_tag: str, lines: list[str]) -> None:
        if battle_tag != self._battle_tag or not lines:
            return
        self._frames.append(list(lines))

    def replay(self) -> dict[str, Any] | None:
        if self._battle_tag is None:
            return None
        return {
            "type": "BATTLE_REPLAY",
            "battle_tag": self._battle_tag,
            "frames": [list(lines) for lines in self._frames],
        }
