import json
from pathlib import Path

from jev_showdown.web.dashboard_stream import DashboardEventStream


FIXTURES = Path(__file__).parents[1] / "fixtures" / "dashboard"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_publish_returns_event_envelope_without_rewriting_raw_event():
    stream = DashboardEventStream()

    state = stream.publish(load_fixture("valid-turn.json"))

    assert state["type"] == "DASHBOARD_STATE"
    assert state["event_type"] == "TURN_DECISION"
    assert state["state"]["kind"] == "event"
    assert state["state"]["current_turn"]["jev"]["response_summary"]["choice"] == "move_dracometeor_tera"
    assert stream.snapshot()["current_turn"]["battle_tag"] == "battle-gen9randombattle-56"


def test_non_dashboard_frame_messages_do_not_duplicate_state():
    stream = DashboardEventStream()

    assert stream.publish({"type": "BATTLE_FRAME", "battle_tag": "battle-1", "lines": ["|turn|1"]}) is None
    assert stream.publish({"type": "STATUS_UPDATE", "status": "READY", "busy": False})["event_type"] == "STATUS_UPDATE"
