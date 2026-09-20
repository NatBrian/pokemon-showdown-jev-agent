# tests/unit/test_web_server.py
import time

import pytest
from fastapi.testclient import TestClient

from jev_showdown.config import Settings
from jev_showdown.web.server import create_app


@pytest.fixture
def test_app():
    settings = Settings(
        showdown_username=None,
        showdown_password=None,
        showdown_server_url="localhost:8000",
        jev_endpoint="https://opencode.ai/zen/v1/systemone",
        jev_model="jev-1.13-free",
        jev_auth_token="Bearer public",
        jev_timeout_seconds=5.0,
        battle_format="gen9randombattle",
        dashboard_port=8000,
    )
    return create_app(settings)


def test_http_index(test_app):
    client = TestClient(test_app)
    response = client.get("/")
    assert response.status_code == 200
    assert "<title>JEV BATTLE AGENT</title>" in response.text


def test_websocket_receives_threadsafe_publish(test_app):
    """publish() must deliver to connected clients even when called from
    another thread (battle telemetry runs on poke_env's background loop)."""
    with TestClient(test_app) as client:
        with client.websocket_connect("/ws") as ws:
            test_app.state.manager.publish(
                {"type": "STATUS_UPDATE", "status": "READY", "busy": False}
            )
            message = ws.receive_json()
            assert message["type"] == "STATUS_UPDATE"
            assert message["status"] == "READY"
            assert message["busy"] is False


def test_websocket_replays_battle_frames_to_new_client(test_app):
    with TestClient(test_app) as client:
        manager = test_app.state.manager
        manager.publish(
            {
                "type": "BATTLE_START",
                "battle_tag": "battle-gen9randombattle-1",
            }
        )
        manager.publish(
            {
                "type": "BATTLE_FRAME",
                "battle_tag": "battle-gen9randombattle-1",
                "lines": ["|turn|1"],
            }
        )

        with client.websocket_connect("/ws") as ws:
            replay = ws.receive_json()

    assert replay == {
        "type": "BATTLE_REPLAY",
        "battle_tag": "battle-gen9randombattle-1",
        "frames": [["|turn|1"]],
    }


def test_connection_manager_normalizes_empty_and_malformed_frame_lines(test_app):
    manager = test_app.state.manager
    manager.publish(
        {"type": "BATTLE_START", "battle_tag": "battle-gen9randombattle-1"}
    )
    manager.publish(
        {
            "type": "BATTLE_FRAME",
            "battle_tag": "battle-gen9randombattle-1",
            "lines": ["", "  |turn|1  ", "turn|2", None, ">battle-noise"],
        }
    )

    assert manager._battle_frames.replay()["frames"] == [["|turn|1", "|turn|2"]]


def test_start_battle_hook_invoked():
    settings = Settings(
        showdown_username=None,
        showdown_password=None,
        showdown_server_url="localhost:8000",
        jev_endpoint="https://opencode.ai/zen/v1/systemone",
        jev_model="jev-1.13-free",
        jev_auth_token="Bearer public",
        jev_timeout_seconds=5.0,
        battle_format="gen9randombattle",
        dashboard_port=8000,
    )
    calls: list[str] = []

    async def on_start_battle():
        calls.append("START_BATTLE")

    app = create_app(settings, on_start_battle=on_start_battle)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"action": "START_BATTLE"})
            # Give the portal loop a moment to run the scheduled hook task.
            deadline = time.monotonic() + 2.0
            while not calls and time.monotonic() < deadline:
                time.sleep(0.05)
    assert calls == ["START_BATTLE"]


# --- Embedded Showdown client HTML transformations ----------------------

_FRAMEBUST_HTML = (
    "<html><body>"
    "<script>\n// framebust\nif (self === top) {\n"
    "app = new App();\n} else {\nLM.innerHTML += ' IN FRAME';\n"
    "top.location = self.location;\n}\n</script>"
    "</body></html>"
)
_TRACKING_HTML = (
    "<script async src=\"https://hb.vntsm.com/index.js\"></script>"
    "<script>\n(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;"
    "/* ga bootstrap */})();\n</script>"
)


def test_patch_showdown_framebust_replaces_guard():
    from jev_showdown.web.server import patch_showdown_framebust

    patched = patch_showdown_framebust(_FRAMEBUST_HTML)
    assert "if (self === top)" not in patched
    assert "if (true) { /* embedded in Jev dashboard */" in patched


def test_patch_showdown_framebust_fallback_drops_block():
    from jev_showdown.web.server import patch_showdown_framebust

    # Upstream reformatted the guard so the line no longer matches.
    html = (
        "<html><body><script>\n// framebust\nif (self == top) {\n"
        "top.location = self.location;\n}\n</script></body></html>"
    )
    patched = patch_showdown_framebust(html)
    assert "framebust" not in patched
    assert "var app = new App();" in patched


def test_strip_showdown_tracking_removes_ad_scripts():
    from jev_showdown.web.server import strip_showdown_tracking

    stripped = strip_showdown_tracking(
        "<html><body>" + _TRACKING_HTML + "</body></html>"
    )
    assert "vntsm" not in stripped
    assert "GoogleAnalyticsObject" not in stripped


def test_inject_showdown_boot_shim():
    from jev_showdown.web.server import inject_showdown_boot

    injected = inject_showdown_boot(_FRAMEBUST_HTML)
    assert "function jevBoot()" in injected
    assert "Config.server = Config.defaultserver" in injected
    assert "Storage.whenPrefsLoaded.load()" in injected
    # Hash routing is forced so the client does not rewrite the embed URL.
    assert "options.pushState = false" in injected
    # Shim must sit inside the document, right before </body>.
    body = injected.rindex("</body>")
    assert injected.index("jevBoot") < body
    # HTML without a </body> tag still gets the shim.
    assert "jevBoot" in inject_showdown_boot("<html><body>x")
