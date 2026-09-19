import os
from dataclasses import dataclass

from dotenv import load_dotenv
from poke_env.ps_client.server_configuration import (
    LocalhostServerConfiguration,
    ServerConfiguration,
    ShowdownServerConfiguration,
)

@dataclass(frozen=True)
class Settings:
    showdown_username: str | None
    showdown_password: str | None
    showdown_server_url: str
    jev_endpoint: str
    jev_model: str
    jev_auth_token: str
    jev_timeout_seconds: float
    battle_format: str
    dashboard_port: int

def server_configuration_for(server_url: str) -> ServerConfiguration:
    """Map a configured server URL to a poke_env ServerConfiguration.

    poke_env only ships two canned configurations: a local test server at
    ``ws://localhost:8000/showdown/websocket`` and the public Showdown
    server at ``wss://sim3.psim.us/showdown/websocket``. We route any
    localhost/127.0.0.1 host to the local configuration (used by the
    test/benchmark harness) and everything else to the public server.
    """
    host = (server_url or "").split("://")[-1].split("/")[0].lower()
    host = host.split(":")[0]
    if host in ("localhost", "127.0.0.1", ""):
        return LocalhostServerConfiguration
    return ShowdownServerConfiguration


def load_settings() -> Settings:
    load_dotenv()
    auth_token = os.getenv("JEV_AUTH_TOKEN", "Bearer public")
    if auth_token and not auth_token.startswith("Bearer "):
        auth_token = f"Bearer {auth_token}"
    return Settings(
        showdown_username=os.getenv("SHOWDOWN_USERNAME"),
        showdown_password=os.getenv("SHOWDOWN_PASSWORD"),
        showdown_server_url=os.getenv("SHOWDOWN_SERVER_URL", "sim3.psim.us:8000"),
        jev_endpoint=os.getenv("JEV_ENDPOINT", "https://opencode.ai/zen/v1/systemone"),
        jev_model=os.getenv("JEV_MODEL", "jev-1.13-free"),
        jev_auth_token=auth_token,
        jev_timeout_seconds=float(os.getenv("JEV_TIMEOUT_SECONDS", "10.0")),
        battle_format=os.getenv("BATTLE_FORMAT", "gen9randombattle"),
        dashboard_port=int(os.getenv("DASHBOARD_PORT", "8000")),
    )
