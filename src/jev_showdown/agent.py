"""Autonomous Jev Showdown player.

Subclasses poke_env's Player to orchestrate the per-turn decision loop:
enumerate legal candidates -> compute deterministic facts/criteria ->
serialize the battle snapshot -> query Jev -> validate/resolve the order
-> track history and dispatch telemetry.

Also hooks the poke_env battle lifecycle (battle start/finish and raw
battle lines) so the dashboard observes the full battle: opponent moves,
damage, status, stat changes and faints land in the turn history, and
``BATTLE_START`` / ``BATTLE_END`` lifecycle events are emitted for the
orchestrator to drive its public matchmaking flow.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from poke_env.battle import AbstractBattle
from poke_env.player import Player
from poke_env.player.battle_order import BattleOrder

from jev_showdown.battle.candidates import CandidateAction, build_candidate_actions
from jev_showdown.battle.facts import annotate_candidates_with_facts
from jev_showdown.battle.snapshot import BattleSnapshotSerializer
from jev_showdown.battle.validator import ValidatedOrder
from jev_showdown.config import Settings, load_settings
from jev_showdown.decision.opencode_jev import (
    DEFAULT_DECISION_INSTRUCTIONS,
    JevSystemOneClient,
    build_request_payload,
)
from jev_showdown.decision.protocol import JevDecisionResponse
from jev_showdown.strategy.fallback import (
    resolve_order,
    select_deterministic_fallback,
)
from jev_showdown.telemetry.events import BattleEventScanner, TurnHistoryTracker

_SENSITIVE_RESPONSE_KEYS = {
    "authorization",
    "password",
    "token",
    "auth_token",
    "access_token",
    "api_key",
    "apikey",
    "secret",
}


def _redact_observable(value: Any) -> Any:
    """Remove credential-like response fields before dashboard telemetry."""
    if isinstance(value, dict):
        return {
            key: _redact_observable(item)
            for key, item in value.items()
            if str(key).lower().replace("-", "_") not in _SENSITIVE_RESPONSE_KEYS
        }
    if isinstance(value, list):
        return [_redact_observable(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_observable(item) for item in value]
    return value


class JevPlayer(Player):
    """A poke_env Player that delegates move selection to the Jev model."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        jev_client: JevSystemOneClient | None = None,
        serializer: BattleSnapshotSerializer | None = None,
        history_tracker: TurnHistoryTracker | None = None,
        on_turn_event: Callable[[dict[str, Any]], Any] | None = None,
        on_battle_event: Callable[[dict[str, Any]], Any] | None = None,
        on_battle_frame: Callable[[dict[str, Any]], Any] | None = None,
        on_decision_phase: Callable[[dict[str, Any]], Any] | None = None,
        **player_kwargs: Any,
    ) -> None:
        """Initialize the Jev player.

        :param settings: Loaded settings. Defaults to load_settings().
        :param jev_client: Jev decision client. Defaults to a fresh
            JevSystemOneClient built from settings.
        :param serializer: Battle snapshot serializer. Defaults to a fresh
            BattleSnapshotSerializer.
        :param history_tracker: Turn history tracker. Defaults to a fresh
            TurnHistoryTracker.
        :param on_turn_event: Optional callback invoked with a telemetry
            dict after every resolved turn.
        :param on_battle_event: Optional callback invoked with lifecycle
            telemetry (``BATTLE_START`` / ``BATTLE_END``) dicts.
        :param on_battle_frame: Optional callback invoked with one raw
            protocol frame after it has been filtered to a battle room.
        :param on_decision_phase: Optional callback invoked for observable
            decision-pipeline phases before and after Jev evaluation.
        :param player_kwargs: Forwarded to poke_env's Player constructor
            (e.g. account_configuration, battle_format, start_listening).
        """
        self.settings = settings if settings is not None else load_settings()
        super().__init__(**player_kwargs)
        self.jev_client = (
            jev_client if jev_client is not None else JevSystemOneClient(self.settings)
        )
        self.serializer = (
            serializer if serializer is not None else BattleSnapshotSerializer()
        )
        self.history_tracker = (
            history_tracker if history_tracker is not None else TurnHistoryTracker()
        )
        self.on_turn_event = on_turn_event
        self.on_battle_event = on_battle_event
        self.on_battle_frame = on_battle_frame
        self.on_decision_phase = on_decision_phase
        self._scanners: dict[str, BattleEventScanner] = {}
        self._decision_sequence = 0
        self._pending_decisions: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------ choose_move

    async def choose_move(self, battle: AbstractBattle) -> BattleOrder:
        """Run the full Jev decision loop for one turn.

        Always returns a legal BattleOrder: on any failure the deterministic
        fallback ladder takes over, so the battle never stalls.
        """
        candidates: dict[str, CandidateAction] = {}
        criteria: dict[str, str] = {}
        snapshot: dict[str, Any] | None = None
        decision_id = self._new_decision_id(battle)
        self._emit_decision_phase(battle, decision_id, "EXTRACTING")
        t_val_start = time.perf_counter()
        try:
            candidates = build_candidate_actions(battle)
            criteria = annotate_candidates_with_facts(battle, candidates)
            snapshot = self.serializer.build_snapshot(battle, candidates)
            request_payload = build_request_payload(
                self.settings.jev_model,
                snapshot,
                criteria,
            )
            self._emit_decision_phase(
                battle,
                decision_id,
                "CALCULATING",
                snapshot=snapshot,
                legal_action_count=len(candidates),
            )
            self._emit_decision_phase(
                battle,
                decision_id,
                "JEV_EVALUATING",
                snapshot=snapshot,
                criteria=criteria,
                question=request_payload["questions"]["action"],
                request_payload=request_payload,
                model=self.settings.jev_model,
            )
            jev_res = await self.jev_client.evaluate_decision(
                state=snapshot, criteria=criteria
            )
        except Exception as exc:
            jev_res = JevDecisionResponse(
                model="unknown",
                choice=None,
                confidence=0.0,
                error=f"Decision pipeline error: {exc}",
            )

        try:
            validated = resolve_order(jev_res, candidates, battle)
        except Exception as exc:
            validated = select_deterministic_fallback(
                candidates, battle, f"Order resolution error: {exc}"
            )
        val_latency_ms = (time.perf_counter() - t_val_start) * 1000.0
        submitted_message = self._submitted_order_message(validated)
        self._emit_decision_phase(
            battle,
            decision_id,
            "LEGAL",
            validation={
                "chosen_id": validated.chosen_id,
                "is_fallback": validated.is_fallback,
                "fallback_reason": validated.fallback_reason,
                "legal_candidates": len(candidates),
                "latency_ms": val_latency_ms,
            },
            is_fallback=validated.is_fallback,
            fallback_reason=validated.fallback_reason,
        )

        self._record_turn(
            battle,
            candidates,
            criteria,
            jev_res,
            validated,
            snapshot,
            val_latency_ms,
            decision_id,
        )
        self._emit_decision_phase(
            battle,
            decision_id,
            "ORDER_SUBMITTED",
            submitted_order={
                "chosen_id": validated.chosen_id,
                "message": submitted_message,
                "is_fallback": validated.is_fallback,
            },
            is_fallback=validated.is_fallback,
        )
        battle_tag = self._battle_tag(battle)
        if battle_tag:
            self._pending_decisions[battle_tag] = {
                "decision_id": decision_id,
                "turn": self._safe_turn(battle),
                "battle_format": self._battle_format(battle),
            }
        self._emit_decision_phase(
            battle,
            decision_id,
            "AWAITING_SHOWDOWN",
            submitted_order={
                "chosen_id": validated.chosen_id,
                "message": submitted_message,
                "is_fallback": validated.is_fallback,
            },
        )
        return validated.order

    def _record_turn(
        self,
        battle: AbstractBattle,
        candidates: dict[str, CandidateAction],
        criteria: dict[str, str],
        jev_res: JevDecisionResponse,
        validated: ValidatedOrder,
        snapshot: dict[str, Any] | None = None,
        val_latency_ms: float = 0.0,
        decision_id: str | None = None,
    ) -> None:
        """Track the resolved turn and dispatch telemetry if a hook is set."""
        turn = self._safe_turn(battle)

        chosen = candidates.get(validated.chosen_id)
        label = chosen.label if chosen is not None else validated.chosen_id
        kind = chosen.kind if chosen is not None else "unknown"

        active_mon = getattr(battle, "active_pokemon", None)
        actor = (
            getattr(active_mon, "species", "Unknown")
            if active_mon is not None
            else "Unknown"
        )

        if validated.is_fallback:
            note = validated.fallback_reason
        elif jev_res.error is not None:
            note = f"Jev error: {jev_res.error}"
        else:
            note = f"confidence={jev_res.confidence:.2f}"

        self.history_tracker.add_event(
            turn=turn,
            actor=actor,
            action=label,
            damage_pct=None,
            status=None,
            note=note,
        )

        jev_request = jev_res.request_payload or {
            "model": jev_res.model,
            "state": snapshot,
            "questions": {
                "action": {
                    "type": "choice",
                    "instructions": DEFAULT_DECISION_INSTRUCTIONS,
                    "criteria": criteria,
                }
            },
        }
        try:
            submitted_message = validated.order.message
        except Exception:
            submitted_message = None

        event_data: dict[str, Any] = {
            "type": "TURN_DECISION",
            "decision_id": decision_id,
            "turn": turn,
            "battle_tag": getattr(battle, "battle_tag", None),
            "battle_format": getattr(battle, "format", "unknown"),
            "chosen_id": validated.chosen_id,
            "label": label,
            "kind": kind,
            "is_fallback": validated.is_fallback,
            "fallback_reason": validated.fallback_reason,
            "snapshot": snapshot,
            "criteria": criteria,
            "question": jev_request.get("questions", {}).get("action", {}),
            "jev_request": jev_request,
            "validation": {
                "chosen_id": validated.chosen_id,
                "is_fallback": validated.is_fallback,
                "fallback_reason": validated.fallback_reason,
                "legal_candidates": len(candidates),
                "latency_ms": val_latency_ms,
                "submitted_order": submitted_message,
            },
            "jev": {
                "model": jev_res.model,
                "choice": jev_res.choice,
                "confidence": jev_res.confidence,
                "probabilities": jev_res.probabilities,
                "latency_ms": jev_res.latency_ms,
                "input_tokens": jev_res.input_tokens,
                "output_tokens": jev_res.output_tokens,
                "cost": jev_res.cost,
                "error": jev_res.error,
            },
            "jev_response": {
                "model": jev_res.model,
                "choice": jev_res.choice,
                "confidence": jev_res.confidence,
                "probabilities": jev_res.probabilities,
                "latency_ms": jev_res.latency_ms,
                "input_tokens": jev_res.input_tokens,
                "output_tokens": jev_res.output_tokens,
                "cost": jev_res.cost,
                "raw_response": _redact_observable(jev_res.raw_response),
                "error": jev_res.error,
            },
            "submitted_order": {
                "chosen_id": validated.chosen_id,
                "message": submitted_message,
                "is_fallback": validated.is_fallback,
            },
            "recent_history": self.history_tracker.get_recent_events(limit=5),
        }

        if self.on_turn_event is not None:
            self.on_turn_event(event_data)

    # ------------------------------------------------------- battle lifecycle

    async def _create_battle(self, split_message: list[str]) -> AbstractBattle:
        battle = await super()._create_battle(split_message)
        self.history_tracker.reset()
        self._pending_decisions.clear()
        if self.on_battle_event is not None:
            try:
                self.on_battle_event(
                    {
                        "type": "BATTLE_START",
                        "battle_tag": battle.battle_tag,
                        "battle_format": self.settings.battle_format,
                    }
                )
            except Exception:
                pass
        return battle

    def _battle_finished_callback(self, battle: AbstractBattle) -> None:
        super()._battle_finished_callback(battle)
        tag = battle.battle_tag
        pending = self._pending_decisions.pop(tag, None)
        if pending:
            self._dispatch_decision_phase(
                {
                    "type": "DECISION_PHASE",
                    "decision_id": pending["decision_id"],
                    "battle_tag": tag,
                    "battle_format": pending["battle_format"],
                    "turn": pending["turn"],
                    "phase": "RESULT_OBSERVED",
                    "observed_commands": ["battle_end"],
                }
            )
        scanner = self._scanners.pop(tag, None)
        if scanner is not None:
            for event in scanner.flush():
                self._merge_scanner_event(tag, event)
        if self.on_battle_event is not None:
            try:
                won = bool(battle.won)
                players = tuple(battle.players or ())
                username = battle.player_username
                if won and username:
                    winner = username
                elif players:
                    winner = next(
                        (name for name in players if name and name != username), None
                    )
                else:
                    winner = None
                self.on_battle_event(
                    {
                        "type": "BATTLE_END",
                        "battle_tag": tag,
                        "battle_format": self.settings.battle_format,
                        "won": won,
                        "total_turns": self._safe_turn(battle),
                        "winner": winner,
                        "n_won": self.n_won_battles,
                        "n_finished": self.n_finished_battles,
                    }
                )
            except Exception:
                pass

    async def _handle_battle_message(self, split_messages: list[list[str]]) -> None:
        # Feed raw battle lines to the dashboard and event scanner (telemetry
        # only; neither must break battle processing), then hand off to
        # poke_env.
        frame = self._protocol_frame(split_messages)
        if frame is not None and self.on_battle_frame is not None:
            tag, lines = frame
            try:
                self.on_battle_frame(
                    {"type": "BATTLE_FRAME", "battle_tag": tag, "lines": lines}
                )
            except Exception:
                pass
        if frame is not None:
            tag, lines = frame
            self._observe_pending_result(tag, lines)
        try:
            self._feed_scanner(split_messages)
        except Exception:
            pass
        await super()._handle_battle_message(split_messages)

    # ------------------------------------------------------- event scanning

    @staticmethod
    def _protocol_frame(
        split_messages: list[list[str]],
    ) -> tuple[str, list[str]] | None:
        if not split_messages or not split_messages[0]:
            return None
        tag = split_messages[0][0].lstrip(">")
        if not tag.startswith("battle-"):
            return None

        lines: list[str] = []
        for index, parts in enumerate(split_messages):
            if not parts:
                continue
            if index == 0 and parts[0].startswith(">"):
                body = "|".join(parts[1:])
            else:
                body = "|".join(parts)
            if body and not body.startswith("|"):
                body = "|" + body
            if body and body != "|ping":
                lines.append(body)
        if not lines:
            return None
        return tag, lines

    def _feed_scanner(self, split_messages: list[list[str]]) -> None:
        frame = self._protocol_frame(split_messages)
        if frame is None:
            return
        tag, lines = frame

        scanner = self._scanners.get(tag)
        if scanner is None:
            scanner = BattleEventScanner()
            self._scanners[tag] = scanner
        for event in scanner.feed_lines(lines):
            self._merge_scanner_event(tag, event)

    def _merge_scanner_event(self, tag: str, event: dict[str, Any]) -> None:
        """Fold a scanned battle event into the turn history.

        Own-side moves/switches are merged into the decision event recorded
        for the same turn (one card per our action), while opponent events
        become their own cards.
        """
        ident = event["actor"]
        side = event.get("side", ident[:2])
        name = ident.split(":", 1)[1].strip() if ":" in ident else ident

        battle = self.battles.get(tag)
        role = getattr(battle, "player_role", None) if battle is not None else None
        if role == side:
            actor = name
        elif role is not None:
            actor = "Opponent"
        else:
            actor = name

        # Merge into an existing decision card when this is our own action.
        if role == side:
            for existing in reversed(self.history_tracker.events[-6:]):
                same_turn = existing.get("turn") == event["turn"]
                # Species ids are lowercased by poke_env while protocol
                # idents are capitalized; compare case-insensitively.
                same_actor = str(existing.get("actor", "")).lower() == actor.lower()
                is_switch = (
                    event.get("kind") == "switch"
                    and str(existing.get("action", "")).lower().startswith("switch")
                )
                if same_turn and (same_actor or is_switch):
                    if event["badges"]:
                        existing["badges"] = list(existing.get("badges", [])) + event[
                            "badges"
                        ]
                    if event["damage_pct"] is not None:
                        existing["damage_pct"] = event["damage_pct"]
                    if event["status"]:
                        existing["status"] = existing.get("status") or event["status"]
                    if event["fainted"]:
                        existing["fainted"] = True
                    return

        self.history_tracker.add_event(
            turn=event["turn"],
            actor=actor,
            action=event["action"],
            damage_pct=event["damage_pct"],
            status=event["status"],
            fainted=event["fainted"],
            badges=event["badges"],
        )

    # ---------------------------------------------------------------- helpers

    def _dispatch_decision_phase(self, event: dict[str, Any]) -> None:
        if self.on_decision_phase is None:
            return
        try:
            self.on_decision_phase(event)
        except Exception:
            pass

    def _emit_decision_phase(
        self,
        battle: AbstractBattle,
        decision_id: str,
        phase: str,
        **payload: Any,
    ) -> None:
        event = {
            "type": "DECISION_PHASE",
            "decision_id": decision_id,
            "battle_tag": self._battle_tag(battle),
            "battle_format": self._battle_format(battle),
            "turn": self._safe_turn(battle),
            "phase": phase,
        }
        event.update(payload)
        self._dispatch_decision_phase(event)

    def _new_decision_id(self, battle: AbstractBattle) -> str:
        self._decision_sequence += 1
        tag = self._battle_tag(battle) or "battle"
        return f"{tag}:{self._safe_turn(battle)}:{self._decision_sequence}"

    @staticmethod
    def _battle_tag(battle: AbstractBattle) -> str | None:
        value = getattr(battle, "battle_tag", None)
        return value if isinstance(value, str) else None

    def _battle_format(self, battle: AbstractBattle) -> str:
        value = getattr(battle, "format", None)
        if isinstance(value, str):
            return value
        return self.settings.battle_format

    @staticmethod
    def _submitted_order_message(validated: ValidatedOrder) -> Any:
        try:
            return validated.order.message
        except Exception:
            return None

    def _observe_pending_result(self, tag: str, lines: list[str]) -> None:
        pending = self._pending_decisions.get(tag)
        if pending is None:
            return
        result_commands = {
            "move",
            "switch",
            "drag",
            "-damage",
            "-heal",
            "-status",
            "-stat",
            "faint",
            "-terastallize",
            "win",
            "tie",
            "cant",
        }
        observed_commands: list[str] = []
        for line in lines:
            parts = line.split("|")
            command = parts[1] if len(parts) > 1 else ""
            if command in result_commands and command not in observed_commands:
                observed_commands.append(command)
        if not observed_commands:
            return
        self._pending_decisions.pop(tag, None)
        self._dispatch_decision_phase(
            {
                "type": "DECISION_PHASE",
                "decision_id": pending["decision_id"],
                "battle_tag": tag,
                "battle_format": pending["battle_format"],
                "turn": pending["turn"],
                "phase": "RESULT_OBSERVED",
                "observed_commands": observed_commands,
            }
        )

    @staticmethod
    def _safe_turn(battle: AbstractBattle) -> int:
        try:
            return int(getattr(battle, "turn", 1))
        except (TypeError, ValueError):
            return 1
