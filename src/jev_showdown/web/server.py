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
import hashlib
import json
import os
import re
import time
from contextlib import asynccontextmanager
from typing import Any, Callable

import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from jev_showdown.config import Settings
from jev_showdown.telemetry.frames import BattleFrameBuffer

# Served at "/" when the full dashboard frontend is not yet deployed.
FALLBACK_INDEX_HTML = (
    '<html><body><h1>AUTONOMOUS "POKÉMON BATTLE" AGENT</h1></body></html>'
)

# --- Embedded official Showdown client (live battle feed) -------------
# The dashboard embeds the real Pokémon Showdown client in an iframe so the
# LIVE BATTLE panel shows the actual game (sprites, animations, move
# effects, avatars, chat). Three adaptations make that work:
#
# 1. The official client ships a "framebust" that refuses to initialize
#    inside an iframe (``if (self === top)``); the HTML served by this
#    server is patched to always initialize.
# 2. The client resolves some asset paths (/config/*.json, /data/*.js,
#    /action.php, ...) against the page origin; a catch-all route proxies
#    them straight through to Showdown.
# 3. Outside its own origin the client waits on a cross-origin storage
#    bridge (crossdomain.php) that never answers, so it never connects; a
#    small boot shim reproduces the same-origin initialization (see
#    ``inject_showdown_boot``).
#
# Everything fetched from Showdown is persisted to a local cache directory
# so the embed keeps working across restarts and brief network outages.
# The live battle itself is unaffected: the client connects straight to the
# real Showdown game server (sim3.psim.us, which allows cross-origin SockJS
# with ``Access-Control-Allow-Origin: *``) using an absolute server address
# from its own config, independent of this origin.
SHOWDOWN_EMBED_URL = "https://play.pokemonshowdown.com/"
SHOWDOWN_INDEX_TTL_SECONDS = 600.0
SHOWDOWN_ASSET_TTL_SECONDS = 3600.0
SHOWDOWN_CACHE_DIR = os.path.join(
    os.path.expanduser("~"), ".jev_showdown", "showdown_client"
)
SHOWDOWN_UNAVAILABLE_HTML = (
    '<html><body style="background:#000;color:#888;font-family:monospace;'
    'display:flex;align-items:center;justify-content:center;height:100vh">'
    "SHOWDOWN CLIENT UNAVAILABLE — CHECK NETWORK</body></html>"
)

_SHOWDOWN_FRAMEBUST_RE = re.compile(r"if \(self === top\) \{")
_SHOWDOWN_FRAMEBUST_BLOCK_RE = re.compile(r"<script>\s*//\s*framebust[\s\S]*?</script>")
_SHOWDOWN_AD_SCRIPT_RE = re.compile(
    r'<script[^>]*src="[^"]*(?:hb\.vntsm\.com|google-analytics\.com)[^"]*"[^>]*></script>'
)
_SHOWDOWN_GA_INLINE_RE = re.compile(
    r"<script>\s*\(function\(i,s,o,g,r,a,m\)\{i\['GoogleAnalyticsObject'\][\s\S]*?</script>"
)
_SHOWDOWN_VM_INLINE_RE = re.compile(
    r"<script>\s*window\.__VM\s*=\s*window\.__VM[\s\S]*?</script>"
)


def patch_showdown_framebust(html: str) -> str:
    """Neutralize the client's iframe guard so it initializes when embedded."""
    patched = _SHOWDOWN_FRAMEBUST_RE.sub(
        "if (true) { /* embedded in Jev dashboard */", html, count=1
    )
    if patched != html:
        return patched
    # Fallback (upstream reformatted the guard): drop the whole framebust
    # script block and initialize the app unconditionally.
    return _SHOWDOWN_FRAMEBUST_BLOCK_RE.sub(
        "<script>var app = new App();</script>", html, count=1
    )


def strip_showdown_tracking(html: str) -> str:
    """Remove ad/tracking scripts so the embedded client stays clean."""
    html = _SHOWDOWN_AD_SCRIPT_RE.sub("", html)
    html = _SHOWDOWN_GA_INLINE_RE.sub("", html)
    html = _SHOWDOWN_VM_INLINE_RE.sub("", html)
    return html


# The client only auto-configures (Config.server + loaded prefs trackers)
# when it runs on its own origin. When embedded on another origin it takes
# the "cross-origin" path, which waits for a postMessage from
# play.pokemonshowdown.com/crossdomain.php — an endpoint that answers with
# an empty body for non-allow-listed origins, so the wait never resolves and
# the client sits at "Loading..." forever (no socket, no room list). This
# boot script reproduces the same-origin initialization: point Config.server
# at the real server and load the prefs/teams trackers so app.connect()
# runs. It polls briefly for ``app`` so it is robust to script ordering.
#
# It also forces hash-based routing: the client's Backbone router uses
# ``Config.root = '/'`` in pushState mode and would rewrite the embed URL
# (/showdown/ -> /showdown -> /), which serves the *dashboard* HTML inside
# the iframe. With pushState disabled the URL path stays put and rooms are
# addressed by hash (#battle-...), matching how the dashboard navigates it.
_SHOWDOWN_BOOT_SCRIPT = (
    "\n<script>\n"
    "(function () {\n"
    "  function jevBoot() {\n"
    "    try {\n"
    "      if (typeof app === 'undefined' || !app) return false;\n"
    "      if (typeof Backbone !== 'undefined' && Backbone.History && Backbone.History.prototype) {\n"
    "        var origStart = Backbone.History.prototype.start;\n"
    "        Backbone.History.prototype.start = function (options) {\n"
    "          options = options || {};\n"
    "          options.pushState = false;\n"
    "          return origStart.call(this, options);\n"
    "        };\n"
    "      }\n"
    "      if (typeof Config !== 'undefined' && (!Config.server || !Config.server.host)) {\n"
    "        Config.server = Config.defaultserver;\n"
    "      }\n"
    "      if (typeof Storage !== 'undefined') {\n"
    "        if (Storage.whenPrefsLoaded && !Storage.whenPrefsLoaded.isLoaded) Storage.whenPrefsLoaded.load();\n"
    "        if (Storage.whenTeamsLoaded && !Storage.whenTeamsLoaded.isLoaded) Storage.whenTeamsLoaded.load();\n"
    "      }\n"
    "      return true;\n"
    "    } catch (e) { return false; }\n"
    "  }\n"
    "  var tries = 0;\n"
    "  var timer = setInterval(function () {\n"
    "    if (jevBoot() || tries++ > 300) clearInterval(timer);\n"
    "  }, 100);\n"
    "})();\n"
    "</script>\n"
)


def inject_showdown_boot(html: str) -> str:
    """Inject the cross-origin boot shim just before </body>."""
    index = html.lower().rfind("</body>")
    if index == -1:
        return html + _SHOWDOWN_BOOT_SCRIPT
    return html[:index] + _SHOWDOWN_BOOT_SCRIPT + html[index:]


def _showdown_cache_path(url: str) -> str:
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()
    return os.path.join(SHOWDOWN_CACHE_DIR, digest + ".bin")


def _read_showdown_cache(url: str) -> tuple[int, bytes, str] | None:
    try:
        with open(_showdown_cache_path(url), "rb") as f:
            raw = f.read()
        head, _, body = raw.partition(b"\n\n")
        status_s, ctype = head.decode("utf-8").split("\t", 1)
        return int(status_s), body, ctype
    except (OSError, ValueError, UnicodeDecodeError):
        return None


def _write_showdown_cache(url: str, status: int, body: bytes, ctype: str) -> None:
    try:
        os.makedirs(SHOWDOWN_CACHE_DIR, exist_ok=True)
        with open(_showdown_cache_path(url), "wb") as f:
            f.write(
                str(status).encode("utf-8")
                + b"\t"
                + ctype.encode("utf-8")
                + b"\n\n"
                + body
            )
    except OSError:
        pass


def _showdown_cache_fresh(url: str, ttl: float) -> bool:
    try:
        return time.time() - os.path.getmtime(_showdown_cache_path(url)) < ttl
    except OSError:
        return False


class ConnectionManager:
    """Tracks active dashboard WebSocket clients and broadcasts to them."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._battle_frames = BattleFrameBuffer()

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Remember the dashboard's event loop (set at app startup)."""
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        """Accept the connection and register it as active."""
        await websocket.accept()
        self.active_connections.append(websocket)
        replay = self._battle_frames.replay()
        if replay is not None:
            try:
                await websocket.send_json(replay)
            except Exception:
                self.disconnect(websocket)

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

    def publish(self, message: dict[str, Any]) -> None:
        """Thread-safe broadcast, callable from any thread or event loop.

        Battle telemetry is produced on poke_env's background POKE_LOOP
        thread, while WebSocket sends must run on the dashboard loop;
        ``run_coroutine_threadsafe`` bridges the two. No-op when no loop
        has been captured yet or the loop is no longer running.
        """
        self._remember_battle_message(message)
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)
        except RuntimeError:
            pass

    def _remember_battle_message(self, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        battle_tag = message.get("battle_tag")
        if not isinstance(battle_tag, str):
            return
        if message_type == "BATTLE_START":
            self._battle_frames.start(battle_tag)
        elif message_type == "BATTLE_FRAME":
            lines = message.get("lines")
            if isinstance(lines, list) and all(isinstance(line, str) for line in lines):
                self._battle_frames.append(battle_tag, lines)


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
    manager = ConnectionManager()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # Needed for thread-safe telemetry publishing (see ConnectionManager).
        manager.set_loop(asyncio.get_running_loop())
        yield

    app = FastAPI(title="Jev Pokémon Showdown Dashboard", lifespan=lifespan)
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

    async def _fetch_upstream(url: str) -> tuple[int, bytes, str] | None:
        try:
            async with httpx.AsyncClient(
                timeout=15.0, follow_redirects=True
            ) as client:
                response = await client.get(url)
                return (
                    response.status_code,
                    response.content,
                    response.headers.get("content-type", "application/octet-stream"),
                )
        except Exception:
            return None

    @app.get("/showdown/", include_in_schema=False)
    async def get_showdown_embed() -> HTMLResponse:
        """Serve the (patched) official Showdown client for the live feed.

        Fresh disk cache is served directly; otherwise upstream is fetched
        and cached. A stale copy keeps serving while upstream is down.
        """
        upstream = SHOWDOWN_EMBED_URL
        cached = _read_showdown_cache(upstream)
        if not _showdown_cache_fresh(upstream, SHOWDOWN_INDEX_TTL_SECONDS):
            fetched = await _fetch_upstream(upstream)
            if fetched is not None:
                status, body, ctype = fetched
                if status == 200:
                    _write_showdown_cache(upstream, status, body, ctype)
                    cached = fetched
        if cached is None:
            return HTMLResponse(SHOWDOWN_UNAVAILABLE_HTML, status_code=502)
        _status, body, _ctype = cached
        html = inject_showdown_boot(
            strip_showdown_tracking(
                patch_showdown_framebust(body.decode("utf-8", "replace"))
            )
        )
        return HTMLResponse(html)

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

    # Catch-all (registered last so dashboard routes win): the embedded
    # client resolves some asset paths against the page origin
    # (/config/*.json, /data/*.js, /action.php, /manifest.json, ...). Proxy
    # them straight through to Showdown so the client behaves as if it were
    # running on its own domain. Results are cached to disk.
    @app.api_route(
        "/{path:path}", methods=["GET", "POST"], include_in_schema=False
    )
    async def proxy_showdown_asset(request: Request, path: str) -> Response:
        upstream = SHOWDOWN_EMBED_URL + path.lstrip("/")
        if request.method == "POST":
            body = await request.body()
            try:
                async with httpx.AsyncClient(
                    timeout=20.0, follow_redirects=True
                ) as client:
                    r = await client.post(upstream, content=body)
                return Response(
                    content=r.content,
                    status_code=r.status_code,
                    media_type=r.headers.get(
                        "content-type", "application/octet-stream"
                    ),
                )
            except Exception:
                return Response(
                    content=b"SHOWDOWN ASSET UNAVAILABLE",
                    status_code=502,
                    media_type="text/plain",
                )
        cached = _read_showdown_cache(upstream)
        if not _showdown_cache_fresh(upstream, SHOWDOWN_ASSET_TTL_SECONDS):
            fetched = await _fetch_upstream(upstream)
            if fetched is not None:
                _write_showdown_cache(upstream, *fetched)
                cached = fetched
        if cached is None:
            return Response(
                content=b"SHOWDOWN ASSET UNAVAILABLE",
                status_code=502,
                media_type="text/plain",
            )
        status, content, ctype = cached
        return Response(content=content, status_code=status, media_type=ctype)

    return app
