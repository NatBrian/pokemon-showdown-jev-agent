"""CLI entrypoint for the autonomous Pokémon Showdown Jev agent.

Commands:
- ``serve``: run the local dashboard web server and agent.
- ``benchmark``: run a local reproducible benchmark suite against
  ``RandomPlayer`` or ``SimpleHeuristicsPlayer``.

Usage:
    python -m jev_showdown.main serve --port 8000
    python -m jev_showdown.main benchmark --opponent random --matches 5
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Any
from contextlib import suppress

import uvicorn

from jev_showdown.agent import JevPlayer
from jev_showdown.config import (
    Settings,
    load_settings,
    server_configuration_for,
)
from jev_showdown.decision.opencode_jev import JevSystemOneClient
from jev_showdown.web.server import ConnectionManager, create_app

# Observable startup sequence for the public showcase flow.
PHASE_CONNECTING = "CONNECTING TO SHOWDOWN"
PHASE_AUTHENTICATING = "AUTHENTICATING"
PHASE_SELECTING = "SELECTING GEN 9 RANDOM BATTLE"
PHASE_SEARCHING = "SEARCHING FOR OPPONENT"
PHASE_READY = "READY"

# Generous safety timeouts for the public matchmaking flow.
CONNECT_TIMEOUT_SECONDS = 20.0
AUTH_TIMEOUT_SECONDS = 20.0
SEARCH_TIMEOUT_SECONDS = 240.0


class BattleOrchestrator:
    """Drives the public Showdown flow behind START JEV BATTLE.

    Publishing observable lifecycle status to the dashboard as the agent
    connects, authenticates, searches the ladder, plays and finishes.
    One active battle session at a time; failures surface as clear error
    states rather than silent stuck buttons.
    """

    def __init__(
        self, settings: Settings, manager: ConnectionManager | None = None
    ) -> None:
        self.settings = settings
        self.manager = manager
        self._session: asyncio.Task | None = None
        self._playing_announced = False
        self._match_found = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def busy(self) -> bool:
        return self._session is not None and not self._session.done()

    # ------------------------------------------------------------- publishing

    def _publish_status(
        self, status: str, busy: bool = True, error: bool = False
    ) -> None:
        if self.manager is None:
            return
        self.manager.publish(
            {
                "type": "STATUS_UPDATE",
                "status": status,
                "busy": busy,
                "error": error,
            }
        )

    def _publish_event(self, event: dict[str, Any]) -> None:
        if self.manager is not None:
            self.manager.publish(event)

    # ------------------------------------------------------ Jev event bridges

    def _on_turn_event(self, event: dict[str, Any]) -> None:
        if not self._playing_announced:
            self._playing_announced = True
            self._publish_status("JEV PLAYING")
        self._publish_event(event)

    def _on_battle_event(self, event: dict[str, Any]) -> None:
        if event.get("type") == "BATTLE_START":
            self._signal_match_found()
            self._publish_status("MATCH FOUND: INITIALIZING BATTLE")
            self._publish_event(event)
        elif event.get("type") == "BATTLE_END":
            self._publish_event(event)

    def _on_battle_frame(self, event: dict[str, Any]) -> None:
        """Forward the authoritative raw protocol frame to the dashboard."""
        self._publish_event(event)

    def _on_telemetry_error(self, event: dict[str, Any]) -> None:
        """Expose recorder failures without interrupting the battle."""
        self._publish_event(event)

    def _signal_match_found(self) -> None:
        """Wake the matchmaking task from any poke-env callback thread."""
        loop = self._loop
        if loop is None or loop.is_closed():
            self._match_found.set()
            return
        loop.call_soon_threadsafe(self._match_found.set)

    # ------------------------------------------------------------------ start

    async def start(self) -> None:
        """Entry point invoked by the dashboard START_BATTLE action."""
        if self.busy:
            return
        self._loop = asyncio.get_running_loop()
        self._match_found.clear()
        self._playing_announced = False
        self._session = asyncio.create_task(self._run())

    async def _run(self) -> None:
        settings = self.settings
        if not settings.showdown_username or not settings.showdown_password:
            self._publish_status(
                "ERROR: SHOWDOWN ACCOUNT NOT CONFIGURED: SET SHOWDOWN_USERNAME / "
                "SHOWDOWN_PASSWORD IN .env",
                busy=False,
                error=True,
            )
            return

        jev_client: JevSystemOneClient | None = None
        player: JevPlayer | None = None
        try:
            self._publish_status(PHASE_CONNECTING)
            jev_client = JevSystemOneClient(settings)
            from poke_env.ps_client.account_configuration import (
                AccountConfiguration,
            )

            player = JevPlayer(
                account_configuration=AccountConfiguration(
                    settings.showdown_username, settings.showdown_password
                ),
                settings=settings,
                jev_client=jev_client,
                on_turn_event=self._on_turn_event,
                on_battle_event=self._on_battle_event,
                on_battle_frame=self._on_battle_frame,
                on_telemetry_error=self._on_telemetry_error,
                battle_format=settings.battle_format,
                server_configuration=server_configuration_for(
                    settings.showdown_server_url
                ),
            )

            if not await self._wait_for(
                lambda: getattr(player.ps_client, "websocket", None) is not None,
                CONNECT_TIMEOUT_SECONDS,
            ):
                self._publish_status(
                    "ERROR: CONNECTION TO SHOWDOWN TIMED OUT",
                    busy=False,
                    error=True,
                )
                return

            self._publish_status(PHASE_AUTHENTICATING)
            if not await self._wait_for(
                lambda: player.ps_client.logged_in.is_set(), AUTH_TIMEOUT_SECONDS
            ):
                self._publish_status(
                "ERROR: SHOWDOWN AUTHENTICATION FAILED: CHECK .env CREDENTIALS",
                    busy=False,
                    error=True,
                )
                return

            # The target format is fixed for the first showcase.
            self._publish_status(PHASE_SELECTING)
            await asyncio.sleep(0.6)
            self._publish_status(PHASE_SEARCHING)

            ladder_task = asyncio.create_task(player.ladder(1))
            try:
                await asyncio.wait_for(
                    self._match_found.wait(), timeout=SEARCH_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                ladder_task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await ladder_task
                self._publish_status(
                "ERROR: OPPONENT SEARCH TIMED OUT: NO OPPONENT FOUND",
                    busy=False,
                    error=True,
                )
                return
            try:
                await ladder_task
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - surface any session failure
                self._publish_status(
                    f"ERROR: BATTLE SESSION FAILED ({exc})",
                    busy=False,
                    error=True,
                )
                return

            self._publish_status(PHASE_READY, busy=False)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - surface any startup failure
            self._publish_status(f"ERROR: {exc}", busy=False, error=True)
        finally:
            self._playing_announced = False
            await self._teardown(player, jev_client)

    # ---------------------------------------------------------------- helpers

    async def _wait_for(self, predicate, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if predicate():
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.1)
        return False

    @staticmethod
    async def _teardown(player: JevPlayer | None, jev_client: JevSystemOneClient | None) -> None:
        if player is not None:
            with suppress(Exception):
                await player.ps_client.stop_listening()
        if jev_client is not None:
            with suppress(Exception):
                await jev_client.aclose()


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Autonomous Pokémon Showdown Agent Powered by Jev AI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # serve command
    serve_parser = subparsers.add_parser(
        "serve", help="Run the local web dashboard and agent"
    )
    serve_parser.add_argument(
        "--port", type=int, default=8000, help="Web dashboard port"
    )

    # benchmark command
    bench_parser = subparsers.add_parser(
        "benchmark", help="Run local reproducible benchmark matches"
    )
    bench_parser.add_argument(
        "--opponent",
        type=str,
        choices=["random", "simple_heuristics"],
        default="random",
        help="Opponent type for the benchmark matches",
    )
    bench_parser.add_argument(
        "--matches", type=int, default=5, help="Number of benchmark matches"
    )

    return parser


def _import_run_benchmark():
    """Import the benchmark runner from the repo-root benchmarks package.

    ``benchmarks`` lives at the repository root (outside the ``src``
    layout), so fall back to adding the repo root to ``sys.path`` when it
    is not already importable.
    """
    try:
        from benchmarks.run_matches import run_benchmark
    except ImportError:
        repo_root = Path(__file__).resolve().parents[2]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from benchmarks.run_matches import run_benchmark
    return run_benchmark


def _serve(settings: Settings, port: int) -> None:
    """Run the dashboard web server and agent (blocking)."""
    orchestrator = BattleOrchestrator(settings)
    # The dashboard's START_BATTLE action drives the orchestrator; the
    # manager (WebSocket hub) is attached once the app has been created.
    app = create_app(settings, on_start_battle=lambda: orchestrator.start())
    orchestrator.manager = app.state.manager
    app.state.orchestrator = orchestrator
    print(f"Starting Jev Showdown Dashboard on http://localhost:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()
    settings = load_settings()

    if args.command == "serve":
        _serve(settings, port=args.port)
    elif args.command == "benchmark":
        run_benchmark = _import_run_benchmark()
        asyncio.run(
            run_benchmark(
                settings,
                opponent_type=args.opponent,
                n_matches=args.matches,
            )
        )


if __name__ == "__main__":
    main()
