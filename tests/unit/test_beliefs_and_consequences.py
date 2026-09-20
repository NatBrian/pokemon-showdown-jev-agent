from types import SimpleNamespace
from unittest.mock import MagicMock

from jev_showdown.battle.beliefs import build_hidden_information_ledger
from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.battle.consequences import compile_action_responses


def _mon(
    species,
    *,
    hp_fraction=1.0,
    fainted=False,
    moves=None,
    status=None,
):
    return SimpleNamespace(
        species=species,
        forme=None,
        current_hp=100 if hp_fraction else 0,
        max_hp=100,
        current_hp_fraction=hp_fraction,
        status=status,
        boosts={"atk": 1},
        effects=set(),
        fainted=fainted,
        moves=moves or [],
        item=None,
        ability=None,
        tera_type=None,
        last_seen_turn=6,
    )


def _battle_with_fog_of_war():
    active = _mon("Heatran", moves=[SimpleNamespace(id="flashcannon")])
    bench = _mon("Rotom-Wash")
    fainted = _mon("Gengar", hp_fraction=0.0, fainted=True)
    return SimpleNamespace(
        turn=7,
        opponent_active_pokemon=active,
        opponent_team={"heatran": active, "rotom": bench, "gengar": fainted},
    )


def test_hidden_ledger_keeps_revealed_and_unknown_slots_separate():
    ledger = build_hidden_information_ledger(_battle_with_fog_of_war())
    slots = ledger["opponent_slots"]

    assert len(slots) == 6
    assert slots[0]["visibility"] == "revealed_active"
    assert slots[1]["visibility"] == "revealed_bench"
    assert slots[2]["visibility"] == "fainted"
    assert slots[3]["visibility"] == "unknown_slot"
    assert slots[0]["moves"][0]["source"] == "observed"
    assert slots[0]["unrevealed_set_details"]["source"] == "unknown"
    assert slots[3]["species"]["value"] is None
    assert slots[3]["species"]["source"] == "unknown"


def test_hidden_ledger_does_not_invent_unknown_species_or_set_details():
    ledger = build_hidden_information_ledger(_battle_with_fog_of_war())

    for slot in ledger["opponent_slots"][3:]:
        assert slot["species"]["value"] is None
        assert slot["moves"] == []
        assert slot["unrevealed_set_details"]["value"] is None
        assert slot["possible_hypotheses"] == []


def test_response_compiler_exposes_categories_without_fabricated_probabilities():
    battle = _battle_with_fog_of_war()
    beliefs = build_hidden_information_ledger(battle)
    candidates = {
        "move_a": CandidateAction(
            id="move_a",
            kind="move",
            label="Move A",
            order_ref=MagicMock(),
            facts={"damage": {"value": [40, 50], "source": "calculated"}},
        ),
        "switch_b": CandidateAction(
            id="switch_b",
            kind="switch",
            label="Switch B",
            order_ref=MagicMock(),
            facts={"species": "Rotom-Wash", "hp_fraction": 1.0},
        ),
    }

    responses = compile_action_responses(battle, candidates, beliefs)
    response = responses["move_a"]

    assert response["action_id"] == "move_a"
    assert response["opponent_stays"]["source"] in {"calculated", "unknown"}
    assert "opponent_uses_known_move" in response
    assert "opponent_uses_unknown_move" in response
    assert "opponent_sets_up_or_statuses" in response
    assert "opponent_switches_revealed" in response
    assert "opponent_switches_unknown" in response
    assert response["opponent_switches_unknown"]["probability"] is None


def test_switch_response_keeps_our_switch_and_opponent_double_switch_separate():
    battle = _battle_with_fog_of_war()
    beliefs = build_hidden_information_ledger(battle)
    candidate = CandidateAction(
        id="switch_b",
        kind="switch",
        label="Switch B",
        order_ref=MagicMock(),
        facts={"species": "Rotom-Wash", "hp_fraction": 0.8},
    )

    response = compile_action_responses(battle, {candidate.id: candidate}, beliefs)[
        candidate.id
    ]

    double_switch = response["double_switch"]
    assert double_switch["our_switch"]["action_id"] == "switch_b"
    assert double_switch["our_switch"]["target_species"] == "Rotom-Wash"
    assert double_switch["opponent_switch"]["unknown"]["probability"] is None
    assert "opponent_switch" not in double_switch["our_switch"]
