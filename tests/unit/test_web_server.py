# tests/unit/test_web_server.py
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
