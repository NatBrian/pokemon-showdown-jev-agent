"""Local dashboard web server and real-time WebSocket hub.

Exposes a FastAPI application that:
- serves the dashboard HTML at ``/`` (``static/index.html`` when present,
  otherwise a minimal fallback page),
- streams battle/telemetry state to connected dashboard clients over the
  ``/ws`` WebSocket, and
- accepts ``{"action": "START_BATTLE"}`` messages from the dashboard to
  trigger battle starts via an injected ``on_start_battle`` hook.
"""
import asyncio
import json
import os
from typing import Any, Callable

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from jev_showdown.config import Settings

# Served at "/" when the full dashboard frontend is not yet deployed.
FALLBACK_INDEX_HTML = (
    '<html><body><h1>AUTONOMOUS "POKÉMON BATTLE" AGENT</h1></body></html>'
)


class ConnectionManager:
    """Tracks active dashboard WebSocket clients and broadcasts to them."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept the connection and register it as active."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a client from the active set (idempotent)."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a JSON message to every active dashboard client.

        Clients that fail to receive are dropped so one bad connection
        cannot break the broadcast loop.
        """
        msg_str = json.dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(msg_str)
            except Exception:
                self.disconnect(connection)


def create_app(
    settings: Settings,
    on_start_battle: Callable[[], Any] | None = None,
) -> FastAPI:
    """Build the dashboard FastAPI application.

    :param settings: Loaded settings, stored on ``app.state.settings``.
    :param on_start_battle: Optional async hook invoked as a background
        asyncio task when a dashboard client sends
        ``{"action": "START_BATTLE"}`` over ``/ws``.
    """
    app = FastAPI(title="Jev Pokémon Showdown Dashboard")
    manager = ConnectionManager()
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)

    app.state.manager = manager
    app.state.settings = settings

    @app.get("/", response_class=HTMLResponse)
    async def get_index() -> str:
        """Serve the dashboard HTML (static/index.html or fallback)."""
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                return f.read()
        return FALLBACK_INDEX_HTML

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """Bi-directional dashboard channel.

        Receives client actions (currently ``START_BATTLE``) and keeps the
        connection registered for server-initiated broadcasts.
        """
        await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if msg.get("action") == "START_BATTLE" and on_start_battle is not None:
                    asyncio.create_task(on_start_battle())
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(websocket)

    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app
