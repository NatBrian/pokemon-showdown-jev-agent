# tests/unit/test_config.py
from poke_env.ps_client.server_configuration import (
    LocalhostServerConfiguration,
    ShowdownServerConfiguration,
)

from jev_showdown.config import load_settings, server_configuration_for


def test_server_configuration_for_local_hosts():
    for url in ("localhost:8000", "127.0.0.1:8000", "localhost", ""):
        assert server_configuration_for(url) is LocalhostServerConfiguration


def test_server_configuration_for_public_hosts():
    for url in ("sim3.psim.us:8000", "sim2.psim.us:8000", "psim.us"):
        assert server_configuration_for(url) is ShowdownServerConfiguration


def test_auth_token_gets_bearer_prefix(monkeypatch):
    monkeypatch.setenv("JEV_AUTH_TOKEN", "rawtoken")
    settings = load_settings()
    assert settings.jev_auth_token == "Bearer rawtoken"


def test_auth_token_bearer_prefix_kept(monkeypatch):
    monkeypatch.setenv("JEV_AUTH_TOKEN", "Bearer abc")
    settings = load_settings()
    assert settings.jev_auth_token == "Bearer abc"
