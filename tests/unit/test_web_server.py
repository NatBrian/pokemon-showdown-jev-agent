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
    assert 'AUTONOMOUS "POKÉMON BATTLE" AGENT' in response.text


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
