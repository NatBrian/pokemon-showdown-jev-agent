# tests/unit/test_config.py
import os
import pytest
from jev_showdown.config import Settings, load_settings

def test_load_settings_defaults(monkeypatch):
    monkeypatch.delenv("SHOWDOWN_USERNAME", raising=False)
    monkeypatch.delenv("SHOWDOWN_PASSWORD", raising=False)
    settings = load_settings()
    assert settings.jev_endpoint == "https://opencode.ai/zen/v1/systemone"
    assert settings.jev_model == "jev-1.13-free"
    assert settings.jev_auth_token == "Bearer public"
    assert settings.jev_timeout_seconds == 10.0
    assert settings.battle_format == "gen9randombattle"
    assert settings.dashboard_port == 8000

def test_load_settings_custom_env(monkeypatch):
    monkeypatch.setenv("SHOWDOWN_USERNAME", "test_bot_jev")
    monkeypatch.setenv("SHOWDOWN_PASSWORD", "secret123")
    monkeypatch.setenv("JEV_TIMEOUT_SECONDS", "5.0")
    settings = load_settings()
    assert settings.showdown_username == "test_bot_jev"
    assert settings.showdown_password == "secret123"
    assert settings.jev_timeout_seconds == 5.0
