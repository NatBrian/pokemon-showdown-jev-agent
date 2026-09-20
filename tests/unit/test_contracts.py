import pytest

from jev_showdown.battle.contracts import (
    BattleRequestMetadata,
    DecisionFingerprint,
    Fact,
    build_decision_fingerprint,
)


def test_fact_serializes_unknown_value_with_provenance_and_unit():
    fact = Fact(
        value=None,
        source="unknown",
        unit="percent_of_target_max_hp",
        confidence=None,
        assumptions=("target set is unrevealed",),
    )

    assert fact.to_dict() == {
        "value": None,
        "source": "unknown",
        "unit": "percent_of_target_max_hp",
        "confidence": None,
        "assumptions": ["target set is unrevealed"],
    }


def test_fact_rejects_confidence_outside_probability_range():
    with pytest.raises(ValueError, match="confidence"):
        Fact(value=1, source="calculated", confidence=1.1)


def test_build_decision_fingerprint_preserves_request_identity_and_candidate_order():
    metadata = BattleRequestMetadata(
        battle_id="battle-gen9randombattle-1",
        request_id="req-4",
        state_version=4,
        turn=3,
        request_type="move",
        force_switch=False,
        wait=False,
        trapped=False,
        maybe_trapped=False,
        deadline_monotonic=123.0,
    )

    fingerprint = build_decision_fingerprint(metadata, ("move_a", "switch_b"))

    assert isinstance(fingerprint, DecisionFingerprint)
    assert fingerprint.battle_id == "battle-gen9randombattle-1"
    assert fingerprint.request_id == "req-4"
    assert fingerprint.state_version == 4
    assert fingerprint.turn == 3
    assert fingerprint.candidate_ids == ("move_a", "switch_b")
