"""Verify both evaluation clients can login to local Showdown without a battle."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fp.websocket_client import PSWebsocketClient
from jev_showdown.agent import JevPlayer
from jev_showdown.config import load_settings
from jev_showdown.decision.opencode_jev import JevSystemOneClient
from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.ps_client.server_configuration import ServerConfiguration


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def main() -> None:
    artifact = Path(os.environ["JEV_EVAL_ARTIFACT_DIR"])
    server_url = os.environ.get(
        "JEV_EVAL_SHOWDOWN_SERVER_URL",
        "ws://localhost:8001/showdown/websocket",
    )
    foul_client = None
    jev_client = None
    result = {
        "type": "CONNECTION_SMOKE",
        "started_at": now(),
        "showdown_server_url": server_url,
        "battle_started": False,
        "jev_api_calls": 0,
        "foul_play_login": False,
        "jev_login": False,
        "errors": [],
    }
    started = time.perf_counter()
    try:
        foul_client = await PSWebsocketClient.create(
            "FoulPlayConnectionSmoke", None, server_url
        )
        await asyncio.wait_for(foul_client.login(), timeout=15)
        result["foul_play_login"] = True
    except Exception as exc:  # noqa: BLE001 - persisted setup evidence
        result["errors"].append(f"foul_play: {type(exc).__name__}: {exc}")
    finally:
        if foul_client is not None:
            await foul_client.close()

    settings = load_settings()
    settings = settings.__class__(
        **{
            **settings.__dict__,
            "showdown_server_url": server_url,
            "battle_format": "gen9randombattle",
        }
    )
    jev_client = JevSystemOneClient(settings)
    player = None
    try:
        player = JevPlayer(
            settings=settings,
            jev_client=jev_client,
            account_configuration=AccountConfiguration("JevConnectionSmoke", None),
            battle_format="gen9randombattle",
            server_configuration=ServerConfiguration(
                server_url, "http://localhost:8001/action.php?"
            ),
        )
        await asyncio.wait_for(player.ps_client.wait_for_login(wait_for=15), timeout=20)
        result["jev_login"] = True
    except Exception as exc:  # noqa: BLE001 - persisted setup evidence
        result["errors"].append(f"jev: {type(exc).__name__}: {exc}")
    finally:
        if player is not None:
            try:
                await player.ps_client.stop_listening()
            except Exception as exc:  # noqa: BLE001 - persisted cleanup evidence
                result["errors"].append(
                    f"jev_cleanup: {type(exc).__name__}: {exc}"
                )
        if jev_client is not None:
            await jev_client.aclose()

    result["finished_at"] = now()
    result["duration_ms"] = (time.perf_counter() - started) * 1000.0
    (artifact / "connection-smoke.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
