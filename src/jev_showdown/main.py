"""CLI entrypoint for the autonomous Pokémon Showdown Jev agent.

Commands:
- ``serve``: run the local dashboard web server and agent.
- ``benchmark``: run a local reproducible benchmark suite against
  ``RandomPlayer`` or ``SimpleHeuristicsPlayer``.

Usage:
    python -m jev_showdown.main serve --port 8000
    python -m jev_showdown.main benchmark --opponent random --matches 5
"""
import argparse
import asyncio
import sys
from pathlib import Path

import uvicorn

from jev_showdown.config import Settings, load_settings
from jev_showdown.web.server import create_app


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


async def _start_battle_placeholder() -> None:
    """Dashboard START_BATTLE hook; wired to matchmaking in Task 11."""
    print("START_BATTLE requested from dashboard")


def _serve(settings: Settings, port: int) -> None:
    """Run the dashboard web server and agent (blocking)."""
    app = create_app(settings, on_start_battle=_start_battle_placeholder)
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
