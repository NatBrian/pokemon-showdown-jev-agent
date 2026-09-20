"""Telemetry and event tracking modules."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

_STATUS_PRETTY: dict[str, str] = {
    "brn": "BURN",
    "psn": "POISON",
    "tox": "TOXIC",
    "par": "PARALYSIS",
    "slp": "SLEEP",
    "frz": "FREEZE",
    "flinch": "FLINCHED",
    "confusion": "CONFUSED",
    "trapped": "TRAPPED",
}

_STAT_PRETTY: dict[str, str] = {
    "atk": "ATK",
    "def": "DEF",
    "spa": "SP.A",
    "spd": "SP.D",
    "spe": "SPE",
    "accuracy": "ACC",
    "evasion": "EVA",
}


@dataclass
class TurnHistoryTracker:
    """Compact, ordered record of what happened in the battle so far."""

    events: list[dict[str, Any]] = field(default_factory=list)

    def reset(self) -> None:
        """Clear all events at the start of a new battle."""
        self.events.clear()

    def add_event(
        self,
        turn: int,
        actor: str,
        action: str,
        damage_pct: int | None = None,
        status: str | None = None,
        note: str | None = None,
        fainted: bool = False,
        badges: list[str] | None = None,
    ) -> None:
        self.events.append(
            {
                "turn": turn,
                "actor": actor,
                "action": action,
                "damage_pct": damage_pct,
                "status": status,
                "note": note,
                "fainted": bool(fainted),
                "badges": list(badges or []),
            }
        )

    def get_recent_events(self, limit: int = 5) -> list[dict[str, Any]]:
        return self.events[-limit:]


@dataclass
class _PendingAction:
    """A move/switch we are still collecting effects for."""

    turn: int
    side: str  # "p1" or "p2"
    ident: str  # e.g. "p1a: Garchomp"
    kind: str  # "move" | "switch"
    action: str  # human label
    damage_pct: int | None = None
    status: str | None = None
    fainted: bool = False
    badges: list[str] = field(default_factory=list)


def _parse_hp(hp_str: str) -> tuple[float, float | None]:
    """Parse a Showdown HP string into (hp, max_hp).

    "95/344" -> (95, 344); "fainted" -> (0, None); "344" -> (344, 344).
    """
    text = (hp_str or "").strip().split()[0]
    if text.lower() in {"fainted", "fnt", "0"}:
        return 0.0, None
    if "/" in text:
        cur, _, mx = text.partition("/")
        try:
            return float(cur), (float(mx) if mx else None)
        except ValueError:
            return 0.0, None
    try:
        return float(text), None
    except ValueError:
        return 0.0, None


class BattleEventScanner:
    """Incrementally converts raw Showdown battle lines into history events.

    The scanner is fed the raw protocol lines of a battle (moves, damage,
    status, stat changes, faints, switches, turn markers) and emits compact
    event dicts that :class:`TurnHistoryTracker` renders as the dashboard's
    TURN HISTORY cards. HP baselines are seeded from ``|request|`` payloads
    so damage percentages are computed against true max HP.
    """

    def __init__(self) -> None:
        self.current_turn: int = 1
        self._pending: list[_PendingAction] = []
        self._hp: dict[str, tuple[float, float | None]] = {}
        # Set once the battle is live (first request/start line). Initial
        # send-outs are not "switches" and must not create history cards.
        self._started: bool = False

    # ------------------------------------------------------------------ feed

    def feed_lines(self, lines: list[str]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for line in lines:
            parts = line.split("|")
            if not parts or not parts[0]:
                parts = parts[1:]
            if not parts:
                continue
            mtype = parts[0]
            # Be tolerant of stray whitespace around protocol arguments.
            args = [a.strip() for a in parts[1:]]
            try:
                # Real Showdown protocol: primary action lines have NO dash
                # (|move|, |switch|, |drag|, |turn|, |faint|) while effect
                # lines are dashed (|-damage|, |-status|, |-stat|, ...).
                # Both spellings are accepted defensively.
                if mtype in ("turn", "-turn"):
                    events.extend(self._flush_all())
                    try:
                        self.current_turn = max(1, int(args[0]))
                    except (IndexError, ValueError):
                        pass
                elif mtype == "request" and args:
                    self._seed_from_request(args[0])
                    self._started = True
                elif mtype == "start":
                    self._started = True
                elif mtype in ("move", "-move"):
                    events.extend(self._begin_action(args, kind="move"))
                elif mtype in ("switch", "drag", "-switch"):
                    events.extend(self._begin_action(args, kind="switch"))
                elif mtype in ("-damage", "-heal"):
                    self._handle_hp(args, is_damage=(mtype == "-damage"))
                elif mtype == "-status":
                    self._handle_status(args)
                elif mtype in ("-stat", "stat"):
                    self._handle_stat(args)
                elif mtype in ("faint", "-faint"):
                    self._handle_faint(args)
                elif mtype == "-terastallize":
                    self._handle_terastallize(args)
            except Exception:
                # Telemetry parsing must never break battle processing.
                continue
        return events

    def flush(self) -> list[dict[str, Any]]:
        return self._flush_all()

    # -------------------------------------------------------------- internal

    @staticmethod
    def _side(ident: str) -> str:
        return ident[:2] if ident and len(ident) >= 2 and ident[:2] in ("p1", "p2") else "?"

    @staticmethod
    def _key(ident: str) -> str:
        """Normalize an ident so request lines and battle lines agree.

        Request payloads use the bare side id ("p1: Garchomp") while battle
        lines use the active slot ("p1a: Garchomp"); both map to one key.
        """
        ident = (ident or "").strip()
        if len(ident) >= 4 and ident[2].isalpha() and ident[3] == ":":
            return ident[:2] + ident[3:]
        return ident

    @staticmethod
    def _name(ident: str) -> str:
        return ident.split(":", 1)[1].strip() if ":" in ident else ident

    @staticmethod
    def _label(move_id: str) -> str:
        return move_id.replace("_", " ").title()

    def _seed_from_request(self, request_json: str) -> None:
        try:
            req = json.loads(request_json)
        except (TypeError, ValueError):
            return
        for mon in (req.get("side") or {}).get("pokemon", []):
            ident = mon.get("ident")
            if ident:
                self._hp[self._key(ident)] = _parse_hp(str(mon.get("condition", "")))

    def _begin_action(self, args: list[str], kind: str) -> list[dict[str, Any]]:
        if not args:
            return []
        src = args[0]
        label = self._name(src) if kind == "switch" else self._label(args[1] if len(args) > 1 else args[0])
        side = self._side(src)

        # Switch lines always carry the incoming mon's HP; seed it even for
        # the initial send-outs.
        if kind == "switch" and len(args) >= 3:
            self._hp[self._key(src)] = _parse_hp(args[2])
        if kind == "switch" and not self._started:
            # Initial send-out: no history card.
            return []

        # A new action by the same side completes the previous pending one.
        events = [self._event(p) for p in self._pending if p.side == side]
        self._pending = [p for p in self._pending if p.side != side]
        self._pending.append(
            _PendingAction(
                turn=self.current_turn,
                side=side,
                ident=src,
                kind=kind,
                action="Switch" if kind == "switch" else label,
            )
        )
        return events

    def _handle_hp(self, args: list[str], is_damage: bool) -> None:
        if len(args) < 2:
            return
        tgt, hp_str = args[0], args[1]
        key = self._key(tgt)
        cur, max_hp = _parse_hp(hp_str)
        prev = self._hp.get(key)
        self._hp[key] = (cur, max_hp)
        if not is_damage or prev is None:
            return
        prev_hp, prev_max = prev
        max_hp_eff = max_hp or prev_max
        if not max_hp_eff:
            return
        delta_pct = int(round((prev_hp - cur) / max_hp_eff * 100))
        if delta_pct <= 0:
            return
        tgt_side = self._side(tgt)
        for pending in reversed(self._pending):
            if pending.side != tgt_side:
                pending.damage_pct = (pending.damage_pct or 0) + delta_pct
                break

    def _handle_status(self, args: list[str]) -> None:
        if len(args) < 2:
            return
        tgt, status = args[0], args[1].strip()
        if not status:
            return
        label = _STATUS_PRETTY.get(status.lower(), status.upper())
        tgt_side = self._side(tgt)
        for pending in reversed(self._pending):
            if pending.side != tgt_side:
                pending.status = label
                break

    def _handle_stat(self, args: list[str]) -> None:
        if len(args) < 3 or not self._pending:
            return
        stat, stage = args[1], args[2].strip()
        try:
            steps = int(stage)
        except ValueError:
            return
        pretty = _STAT_PRETTY.get(stat.lower(), stat.upper())
        self._pending[-1].badges.append(f"{pretty} {steps:+d}")

    def _handle_faint(self, args: list[str]) -> None:
        if not args:
            return
        tgt_side = self._side(args[0])
        for pending in reversed(self._pending):
            if pending.side != tgt_side:
                pending.fainted = True
                break

    def _handle_terastallize(self, args: list[str]) -> None:
        if not args:
            return
        tgt_side = self._side(args[0])
        for pending in reversed(self._pending):
            if pending.side != tgt_side:
                if "TERA" not in pending.badges:
                    pending.badges.append("TERA")
                break

    def _event(self, pending: _PendingAction) -> dict[str, Any]:
        return {
            "turn": pending.turn,
            "actor": pending.ident,
            "side": pending.side,
            "kind": pending.kind,
            "action": pending.action,
            "damage_pct": pending.damage_pct,
            "status": pending.status,
            "fainted": pending.fainted,
            "badges": list(pending.badges),
        }

    def _flush_all(self) -> list[dict[str, Any]]:
        events = [self._event(p) for p in self._pending]
        self._pending = []
        return events
