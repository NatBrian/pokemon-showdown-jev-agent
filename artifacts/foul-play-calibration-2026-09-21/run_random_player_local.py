"""Run one free local RandomPlayer ladder battle for Foul Play calibration."""

from __future__ import annotations

import asyncio
import json
import time

from poke_env.player import RandomPlayer
from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.ps_client.server_configuration import ServerConfiguration


async def main() -> None:
    server = ServerConfiguration(
        "ws://localhost:8001/showdown/websocket",
        "http://localhost:8001/action.php?",
    )
    player = RandomPlayer(
        account_configuration=AccountConfiguration("RandomCalibration", None),
        battle_format="gen9randombattle",
        server_configuration=server,
        start_timer_on_battle_start=True,
        save_replays=True,
    )
    started = time.time()
    error = None
    try:
        await asyncio.wait_for(player.ladder(1), timeout=900)
    except Exception as exc:  # preserve the diagnostic outcome for the audit
        error = f"{type(exc).__name__}: {exc}"
    finally:
        player.ps_client.stop_listening()
    print(
        json.dumps(
            {
                "type": "FOUL_PLAY_CALIBRATION_RANDOM_PLAYER",
                "finished_battles": player.n_finished_battles,
                "wins": player.n_won_battles,
                "losses": player.n_lost_battles,
                "ties": player.n_tied_battles,
                "elapsed_seconds": round(time.time() - started, 3),
                "error": error,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
