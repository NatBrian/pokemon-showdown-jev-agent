from types import SimpleNamespace

from jev_showdown.battle.state import extract_request_metadata


def _battle(**overrides):
    values = {
        "last_request": {"rqid": "req-4", "active": [{"moves": []}]},
        "turn": 3,
        "battle_tag": "battle-gen9randombattle-1",
        "wait": False,
        "force_switch": False,
        "trapped": False,
        "maybe_trapped": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_extracts_normal_move_request_metadata():
    metadata = extract_request_metadata(
        _battle(),
        state_version=4,
        deadline_monotonic=123.0,
    )

    assert metadata.request_id == "req-4"
    assert metadata.request_type == "move"
    assert metadata.force_switch is False
    assert metadata.wait is False
    assert metadata.state_version == 4
    assert metadata.turn == 3
    assert metadata.battle_id == "battle-gen9randombattle-1"
    assert metadata.deadline_monotonic == 123.0


def test_wait_takes_priority_over_other_request_classification():
    metadata = extract_request_metadata(
        _battle(wait=True, force_switch=True),
        state_version=8,
    )

    assert metadata.request_type == "wait"
    assert metadata.wait is True
    assert metadata.force_switch is True


def test_force_switch_is_detected_from_request_when_attribute_is_missing():
    metadata = extract_request_metadata(
        _battle(
            force_switch=False,
            last_request={"rqid": "req-switch", "forceSwitch": [True]},
        ),
        state_version=9,
    )

    assert metadata.request_type == "switch"
    assert metadata.force_switch is True


def test_missing_request_fields_are_unknown_or_safe_defaults():
    metadata = extract_request_metadata(
        _battle(last_request={}, turn=None, battle_tag=None),
        state_version=10,
    )

    assert metadata.request_id is None
    assert metadata.request_type == "unknown"
    assert metadata.battle_id is None
    assert metadata.turn == 0
    assert metadata.force_switch is False
    assert metadata.wait is False
