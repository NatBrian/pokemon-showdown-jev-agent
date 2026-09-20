"""Local controlled benchmark suite.

Runs headless battles between the Jev-driven player and a fixed opponent
(``RandomPlayer`` or ``SimpleHeuristicsPlayer``) and reports the Jev win
rate as a percentage. Both players connect to the configured Showdown
server so battles are mediated exactly like online ones, keeping the
evaluation reproducible.
"""
from poke_env.player import RandomPlayer, SimpleHeuristicsPlayer

from benchmarks.evaluation import latency_percentiles, summarize_series
from jev_showdown.agent import JevPlayer
from jev_showdown.config import Settings, server_configuration_for
from jev_showdown.decision.opencode_jev import JevSystemOneClient


async def run_benchmark(
    settings: Settings,
    opponent_type: str = "random",
    n_matches: int = 5,
) -> float:
    """Run ``n_matches`` battles of Jev against the chosen opponent.

    :param settings: Loaded settings (endpoint, battle format, etc.).
    :param opponent_type: "random" for ``RandomPlayer`` or
        "simple_heuristics" for ``SimpleHeuristicsPlayer``.
    :param n_matches: Number of battles to run.
    :return: Jev win rate percentage, e.g. 60.0 for 3/5 wins.
    """
    server_configuration = server_configuration_for(settings.showdown_server_url)
    jev_client = JevSystemOneClient(settings)
    events: list[dict] = []
    jev_player = JevPlayer(
        settings=settings,
        jev_client=jev_client,
        battle_format=settings.battle_format,
        server_configuration=server_configuration,
        on_turn_event=events.append,
        on_battle_event=events.append,
    )

    if opponent_type == "simple_heuristics":
        opponent = SimpleHeuristicsPlayer(
            battle_format=settings.battle_format,
            server_configuration=server_configuration,
        )
    else:
        opponent = RandomPlayer(
            battle_format=settings.battle_format,
            server_configuration=server_configuration,
        )

    print(
        f"Starting benchmark: Jev vs {opponent_type} for {n_matches} "
        "battles..."
    )
    await jev_player.battle_against(opponent, n_battles=n_matches)

    win_rate = (jev_player.n_won_battles / n_matches) * 100
    metrics = summarize_series(events)
    percentiles = latency_percentiles(metrics.decision_latencies_ms)
    print(
        f"Benchmark Complete! format={settings.battle_format} "
        f"opponent={opponent_type} battles={metrics.battles} "
        f"wins={metrics.wins} losses={metrics.losses} draws={metrics.draws} "
        f"win_rate={win_rate:.1f}% decisions={metrics.decisions} "
        f"fallbacks={metrics.fallbacks} illegal={metrics.illegal_actions} "
        f"stale={metrics.stale_responses} "
        f"latency_ms={percentiles}"
    )
    await jev_client.aclose()
    return win_rate
