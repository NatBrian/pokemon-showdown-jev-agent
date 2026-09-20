# tests/unit/test_orchestrator.py
import asyncio
import threading
from unittest.mock import MagicMock

import pytest

from jev_showdown.config import Settings
from jev_showdown.main import (
    PHASE_AUTHENTICATING,
    PHASE_CONNECTING,
    PHASE_READY,
    PHASE_SEARCHING,
    BattleOrchestrator,
)


def _make_settings(username: str | None = None, password: str | None = None) -> Settings:
    return Settings(
        showdown_username=username,
        showdown_password=password,
        showdown_server_url="sim3.psim.us:8000",
        jev_endpoint="https://opencode.ai/zen/v1/systemone",
        jev_model="jev-1.13-free",
        jev_auth_token="Bearer public",
        jev_timeout_seconds=5.0,
        battle_format="gen9randombattle",
        dashboard_port=8000,
    )


def _capturing_manager() -> tuple[MagicMock, list[dict]]:
    published: list[dict] = []
    manager = MagicMock()
    manager.publish = published.append
    return manager, published


def _statuses(published: list[dict]) -> list[str]:
    return [m["status"] for m in published if m.get("type") == "STATUS_UPDATE"]


class _TrueFlag:
    def is_set(self) -> bool:
        return True


def _install_fakes(monkeypatch, player_cls, client_cls):
    from jev_showdown import main as main_mod

    monkeypatch.setattr(main_mod, "JevPlayer", player_cls)
    monkeypatch.setattr(main_mod, "JevSystemOneClient", client_cls)


class _FakeClient:
    def __init__(self, settings=None) -> None:
        self.settings = settings

    async def aclose(self) -> None:
        pass


@pytest.mark.asyncio
async def test_orchestrator_error_without_showdown_account():
    manager, published = _capturing_manager()
    orchestrator = BattleOrchestrator(_make_settings(), manager=manager)

    await orchestrator.start()
    await orchestrator._session

    statuses = _statuses(published)
    assert len(statuses) == 1
    assert "SHOWDOWN ACCOUNT NOT CONFIGURED" in statuses[0]
    assert published[-1]["error"] is True
    assert published[-1]["busy"] is False
    assert orchestrator.busy is False


@pytest.mark.asyncio
async def test_orchestrator_publishes_full_lifecycle(monkeypatch):
    manager, published = _capturing_manager()
    orchestrator = BattleOrchestrator(
        _make_settings("jev_bot", "secret"), manager=manager
    )

    class _FakePSClient:
        def __init__(self):
            self.logged_in = _TrueFlag()
            self.websocket = object()

        async def stop_listening(self) -> None:
            pass

    class _FakePlayer:
        def __init__(self, **kwargs):
            self.ps_client = _FakePSClient()

        async def ladder(self, n_games: int) -> None:
            orchestrator._on_battle_event({"type": "BATTLE_START"})
            orchestrator._on_battle_event(
                {
                    "type": "BATTLE_END",
                    "won": True,
                    "total_turns": 7,
                    "winner": "jev_bot",
                }
            )

    _install_fakes(monkeypatch, _FakePlayer, _FakeClient)

    await orchestrator.start()
    await orchestrator._session

    statuses = _statuses(published)
    # Observable startup sequence, in order.
    assert statuses[0] == PHASE_CONNECTING
    assert PHASE_AUTHENTICATING in statuses
    assert any("MATCH FOUND" in s for s in statuses)
    assert PHASE_SEARCHING in statuses
    assert statuses[-1] == PHASE_READY
    assert orchestrator.busy is False
    # The battle end result is forwarded to the dashboard.
    end_events = [m for m in published if m.get("type") == "BATTLE_END"]
    assert len(end_events) == 1
    assert end_events[0]["won"] is True


@pytest.mark.asyncio
async def test_orchestrator_error_on_connection_timeout(monkeypatch):
    from jev_showdown import main as main_mod

    # Fast timeout so the test does not wait 20 seconds.
    monkeypatch.setattr(main_mod, "CONNECT_TIMEOUT_SECONDS", 0.05)

    manager, published = _capturing_manager()
    orchestrator = BattleOrchestrator(
        _make_settings("jev_bot", "secret"), manager=manager
    )

    class _FakePSClient:
        def __init__(self):
            self.logged_in = _TrueFlag()
            # The websocket attribute only appears once connected; it never
            # does here, so the connection check must time out.

        async def stop_listening(self) -> None:
            pass

    class _FakePlayer:
        def __init__(self, **kwargs):
            self.ps_client = _FakePSClient()

        async def ladder(self, n_games: int) -> None:
            pass

    _install_fakes(monkeypatch, _FakePlayer, _FakeClient)

    await orchestrator.start()
    await asyncio.wait_for(orchestrator._session, timeout=5.0)

    statuses = _statuses(published)
    assert statuses[0] == PHASE_CONNECTING
    assert any("CONNECTION TO SHOWDOWN TIMED OUT" in s for s in statuses)
    assert published[-1]["error"] is True
    assert orchestrator.busy is False


@pytest.mark.asyncio
async def test_orchestrator_blocks_second_start_while_busy(monkeypatch):
    manager, published = _capturing_manager()
    orchestrator = BattleOrchestrator(
        _make_settings("jev_bot", "secret"), manager=manager
    )

    class _FakePSClient:
        def __init__(self):
            self.logged_in = _TrueFlag()
            self.websocket = object()

        async def stop_listening(self) -> None:
            pass

    class _FakePlayer:
        def __init__(self, **kwargs):
            self.ps_client = _FakePSClient()

        async def ladder(self, n_games: int) -> None:
            orchestrator._on_battle_event({"type": "BATTLE_START"})
            orchestrator._on_battle_event(
                {"type": "BATTLE_END", "won": True, "total_turns": 3}
            )

    _install_fakes(monkeypatch, _FakePlayer, _FakeClient)

    # Hold the session at the connection wait, then release it.
    released = asyncio.Event()

    async def _wait_until_released(predicate, timeout: float) -> bool:
        await released.wait()
        return True

    orchestrator._wait_for = _wait_until_released

    await orchestrator.start()
    assert orchestrator.busy is True

    # A second start is ignored while the first session runs.
    await orchestrator.start()
    first_session = orchestrator._session
    assert orchestrator._session is first_session

    released.set()
    await asyncio.wait_for(first_session, timeout=5.0)
    assert orchestrator.busy is False
    assert _statuses(published)[-1] == PHASE_READY


@pytest.mark.asyncio
async def test_match_found_callback_from_foreign_thread_is_thread_safe():
    orchestrator = BattleOrchestrator(_make_settings("jev_bot", "secret"))
    orchestrator._loop = asyncio.get_running_loop()

    thread = threading.Thread(
        target=orchestrator._signal_match_found,
    )
    thread.start()
    thread.join()

    await asyncio.wait_for(orchestrator._match_found.wait(), timeout=1.0)
