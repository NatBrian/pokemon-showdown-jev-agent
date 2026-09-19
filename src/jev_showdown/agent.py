"""Autonomous Jev Showdown player.

Subclasses poke_env's Player to orchestrate the per-turn decision loop:
enumerate legal candidates -> compute deterministic facts/criteria ->
serialize the battle snapshot -> query Jev -> validate/resolve the order
-> track history and dispatch telemetry.
"""
from typing import Any, Callable

from poke_env.battle import AbstractBattle
from poke_env.player import Player
from poke_env.player.battle_order import BattleOrder

from jev_showdown.battle.candidates import CandidateAction, build_candidate_actions
from jev_showdown.battle.facts import annotate_candidates_with_facts
from jev_showdown.battle.snapshot import BattleSnapshotSerializer
from jev_showdown.battle.validator import ValidatedOrder
from jev_showdown.config import Settings, load_settings
from jev_showdown.decision.opencode_jev import JevSystemOneClient
from jev_showdown.decision.protocol import JevDecisionResponse
from jev_showdown.strategy.fallback import (
    resolve_order,
    select_deterministic_fallback,
)
from jev_showdown.telemetry.events import TurnHistoryTracker


class JevPlayer(Player):
    """A poke_env Player that delegates move selection to the Jev model."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        jev_client: JevSystemOneClient | None = None,
        serializer: BattleSnapshotSerializer | None = None,
        history_tracker: TurnHistoryTracker | None = None,
        on_turn_event: Callable[[dict[str, Any]], None] | None = None,
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

    async def choose_move(self, battle: AbstractBattle) -> BattleOrder:
        """Run the full Jev decision loop for one turn.

        Always returns a legal BattleOrder: on any failure the deterministic
        fallback ladder takes over, so the battle never stalls.
        """
        candidates: dict[str, CandidateAction] = {}
        try:
            candidates = build_candidate_actions(battle)
            criteria = annotate_candidates_with_facts(battle, candidates)
            snapshot = self.serializer.build_snapshot(battle, candidates)
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

        self._record_turn(battle, candidates, jev_res, validated)
        return validated.order

    def _record_turn(
        self,
        battle: AbstractBattle,
        candidates: dict[str, CandidateAction],
        jev_res: JevDecisionResponse,
        validated: ValidatedOrder,
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

        event_data: dict[str, Any] = {
            "turn": turn,
            "battle_format": getattr(battle, "format", "unknown"),
            "chosen_id": validated.chosen_id,
            "label": label,
            "kind": kind,
            "is_fallback": validated.is_fallback,
            "fallback_reason": validated.fallback_reason,
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
            "recent_history": self.history_tracker.get_recent_events(limit=5),
        }

        if self.on_turn_event is not None:
            self.on_turn_event(event_data)

    @staticmethod
    def _safe_turn(battle: AbstractBattle) -> int:
        try:
            return int(getattr(battle, "turn", 1))
        except (TypeError, ValueError):
            return 1
