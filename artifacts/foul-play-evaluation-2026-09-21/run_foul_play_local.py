"""Run the pinned Foul Play checkout against the local Showdown server.

This evaluation-only launcher avoids Foul Play's public-server guest assertion
request. The local Showdown checkout is explicitly configured with
``noguestsecurity`` for offline development, so a blank guest assertion is the
correct local protocol. The Foul Play checkout itself is not modified.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

FOUL_PLAY_ROOT = Path(
    os.environ.get(
        "FOUL_PLAY_ROOT",
        r"C:\Users\Admin\Documents\Github\_bot-research\foul-play",
    )
).resolve()
sys.path.insert(0, str(FOUL_PLAY_ROOT))

from fp.main import run_foul_play
from fp.websocket_client import PSWebsocketClient


async def local_login(self: PSWebsocketClient) -> str:
    """Login as an unregistered local guest without contacting public PS."""

    await self.get_id_and_challstr()
    await self.send_message("", [f"/trn {self.username},0,"])
    await asyncio.sleep(3)
    logging.getLogger(__name__).info("Logged in to local Showdown as %s", self.username)
    return self.username


PSWebsocketClient.login = local_login


if __name__ == "__main__":
    asyncio.run(run_foul_play())
