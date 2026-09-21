import json
from pathlib import Path

from fastapi.testclient import TestClient

from jev_showdown.config import Settings
from jev_showdown.web.server import create_app


FIXTURES = Path(__file__).parents[1] / "fixtures" / "dashboard"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def make_app():
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


def test_live_dashboard_path_projects_turn_and_completion():
    app = make_app()
    fixture = load_fixture("valid-turn.json")
    with TestClient(app) as client:
        manager = app.state.manager
        manager.publish({"type": "BATTLE_START", "battle_tag": fixture["battle_tag"]})
        manager.publish(fixture)
        manager.publish({
            "type": "BATTLE_END",
            "battle_tag": fixture["battle_tag"],
            "winner": "p1",
            "won": True,
            "total_turns": 1,
            "n_finished": 1,
        })
        state = manager.dashboard_snapshot()
        response = client.get("/")

    assert response.status_code == 200
    assert state["battle"]["state"] == "complete"
    assert state["battle"]["total_turns"] == 1
    assert state["history"][0]["jev"]["response_summary"]["choice"] == "move_dracometeor_tera"
    assert state["history"][0]["adapter"]["submitted_order"]["message"].startswith("/choose ")


def test_live_dashboard_path_keeps_fallback_degraded_and_truthful():
    app = make_app()
    fixture = load_fixture("fallback-turn.json")
    with TestClient(app):
        app.state.manager.publish({"type": "BATTLE_START", "battle_tag": fixture["battle_tag"]})
        app.state.manager.publish(fixture)
        state = app.state.manager.dashboard_snapshot()

    turn = state["current_turn"]
    assert turn["lifecycle_state"] == "FALLBACK USED"
    assert turn["adapter"]["fallback"]["reason"] == "Provider HTTP 503; First legal candidate"
    assert turn["jev"]["response_summary"]["probabilities"] is None
    assert turn["jev"]["response_summary"]["input_tokens"] is None
    assert state["metrics"]["fallbacks"] == 1
    assert state["metrics"]["provider_503_errors"] == 1


def test_new_live_connection_receives_dashboard_snapshot_without_replay():
    app = make_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            message = websocket.receive_json()

    assert message["type"] == "DASHBOARD_STATE"
    assert message["state"]["battle"]["replay"] == "unknown"
    assert message["state"]["renderer"]["state"] == "idle"
