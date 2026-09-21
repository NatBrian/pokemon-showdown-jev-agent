import json
from pathlib import Path

from jev_showdown.web.dashboard_state import DashboardProjector, redact_dashboard_value


FIXTURES = Path(__file__).parents[1] / "fixtures" / "dashboard"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_valid_turn_projection_preserves_sources_and_decision_boundary():
    projector = DashboardProjector()

    projector.apply_event(load_fixture("valid-turn.json"))
    view = projector.snapshot()
    turn = view["current_turn"]

    assert view["schema_version"] == 1
    assert turn["battle_tag"] == "battle-gen9randombattle-56"
    assert turn["harness"]["request_metadata"]["rqid"] == 3
    assert turn["harness"]["request_metadata"]["state_version"] == 1
    assert turn["harness"]["handoff_summary"]["candidate_count"] == 13
    assert turn["jev"]["response_summary"]["choice"] == "move_dracometeor_tera"
    assert turn["jev"]["probability_status"] == "valid"
    assert turn["adapter"]["submitted_order"]["message"] == "/choose move dracometeor terastallize"
    assert turn["harness"]["unknowns"]
    assert turn["harness"]["calculated_facts"][0]["source"] == "harness"


def test_fallback_is_not_presented_as_jev_success():
    projector = DashboardProjector()

    projector.apply_event(load_fixture("fallback-turn.json"))
    turn = projector.snapshot()["current_turn"]

    assert turn["adapter"]["fallback"]["is_fallback"] is True
    assert turn["adapter"]["fallback"]["reason"] == "Provider HTTP 503; First legal candidate"
    assert turn["jev"]["response_summary"]["error"] == "HTTP 503"
    assert turn["jev"]["response_summary"]["probabilities"] is None
    assert turn["jev"]["response_summary"]["input_tokens"] is None
    assert turn["adapter"]["submitted_order"]["message"] == "/choose move dracometeor"


def test_invalid_probability_keeps_rejected_map_out_of_valid_distribution():
    projector = DashboardProjector()

    projector.apply_event(load_fixture("invalid-probability.json"))
    turn = projector.snapshot()["current_turn"]

    assert turn["jev"]["probability_status"] == "rejected"
    assert turn["jev"]["response_summary"]["probabilities"] is None
    assert turn["jev"]["response_summary"]["error"] == "Invalid Jev Choice response: probability sum must equal 1.0"
    assert turn["jev"]["raw_response"]["answers"]["action"]["probabilities"]["move_closecombat"] == 0.68


def test_new_battle_clears_history_and_selection():
    projector = DashboardProjector()

    for event in load_fixture("battle-reset.json"):
        projector.apply_event(event)

    view = projector.snapshot()
    assert view["battle"]["battle_tag"] == "battle-gen9randombattle-57"
    assert view["history"] == []
    assert view["current_turn"] is None
    assert view["inspection"] is None


def test_redaction_removes_credential_like_fields_without_destroying_structure():
    redacted = redact_dashboard_value({
        "authorization": "Bearer secret-token",
        "api_key": "private",
        "nested": {"password": "secret", "visible": "ok"},
    })

    assert redacted["authorization"] == "[REDACTED]"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["nested"]["visible"] == "ok"
