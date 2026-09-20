import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from poke_env.battle import Move, Pokemon
from poke_env.player.battle_order import DefaultBattleOrder, SingleBattleOrder

from jev_showdown.battle.beliefs import build_hidden_information_ledger
from jev_showdown.battle.candidates import CandidateAction, build_candidate_actions
from jev_showdown.battle.facts import annotate_candidates_with_facts
from jev_showdown.battle.state import extract_request_metadata


def _cases():
    fixture_path = __file__.replace("test_mechanics_fixtures.py", "../fixtures/mechanics_cases.json")
    with open(fixture_path, encoding="utf-8") as handle:
        return json.load(handle)


def _fact_candidate(move_type="GROUND", *, order_ref=None):
    return CandidateAction(
        id="move_fixture",
        kind="move",
        label="Fixture Move",
        order_ref=order_ref or MagicMock(),
        facts={
            "base_power": 100,
            "type": move_type,
            "category": "PHYSICAL",
            "accuracy": 100,
            "pp": 10,
        },
    )


def _expected_matches(actual, expected):
    assert actual["value"] == expected["value"]
    assert actual["unit"] == expected["unit"]
    assert actual["source"] == expected["source"]
    assert actual["assumptions"] == expected["assumptions"]


def test_type_chart_fixtures_match_labelled_facts():
    cases = {case["id"]: case for case in _cases()["cases"]}
    for case_id in ("type_immunity", "dual_type_4x"):
        case = cases[case_id]
        inputs = case["observed_inputs"]
        battle = SimpleNamespace(
            opponent_active_pokemon=SimpleNamespace(
                type_1=SimpleNamespace(name=inputs["defender_type_1"]),
                type_2=(
                    SimpleNamespace(name=inputs["defender_type_2"])
                    if inputs["defender_type_2"]
                    else None
                ),
                current_hp_fraction=1.0,
            )
        )
        candidate = _fact_candidate(inputs["move_type"])

        annotate_candidates_with_facts(battle, {candidate.id: candidate})

        _expected_matches(candidate.facts[case["expected"]["field"]], case["expected"])


def test_exact_damage_fixture_uses_percent_of_target_max_hp(monkeypatch):
    case = next(case for case in _cases()["cases"] if case["id"] == "known_exact_damage_range")
    inputs = case["observed_inputs"]
    battle = MagicMock()
    battle.active_pokemon = SimpleNamespace(identifier=inputs["attacker_identifier"])
    battle.opponent_active_pokemon = SimpleNamespace(
        identifier=inputs["defender_identifier"],
        max_hp=inputs["target_max_hp"],
        current_hp_fraction=1.0,
        type_1=SimpleNamespace(name="FIRE"),
        type_2=SimpleNamespace(name="STEEL"),
    )
    candidate = _fact_candidate(
        order_ref=SingleBattleOrder(Move("earthquake", 9))
    )
    monkeypatch.setattr(
        "jev_showdown.battle.facts.calculate_damage",
        lambda *args: tuple(inputs["raw_damage_range"]),
    )

    annotate_candidates_with_facts(battle, {candidate.id: candidate})

    _expected_matches(candidate.facts["damage"], case["expected"])


def test_switch_hazard_fixture_remains_unknown_without_verified_calculation():
    case = next(case for case in _cases()["cases"] if case["id"] == "hazard_switch_in")
    candidate = CandidateAction(
        id="switch_fixture",
        kind="switch",
        label="Switch to Rotom-Wash",
        order_ref=MagicMock(),
        facts={
            "species": case["observed_inputs"]["switch_species"],
            "hp_fraction": case["observed_inputs"]["hp_fraction"],
            "status": case["observed_inputs"]["status"],
        },
    )
    battle = SimpleNamespace(opponent_active_pokemon=None)

    annotate_candidates_with_facts(battle, {candidate.id: candidate})

    _expected_matches(
        candidate.facts["consequences"]["entry_hazard_damage"], case["expected"]
    )


def test_status_fixture_is_observed_not_guessed():
    case = next(case for case in _cases()["cases"] if case["id"] == "status_effect")
    mon = SimpleNamespace(
        species=case["observed_inputs"]["species"],
        status=SimpleNamespace(name=case["observed_inputs"]["status"]),
        moves=[],
        fainted=False,
        current_hp=100,
        max_hp=100,
        current_hp_fraction=1.0,
    )
    ledger = build_hidden_information_ledger(
        SimpleNamespace(turn=3, opponent_active_pokemon=mon, opponent_team={})
    )

    _expected_matches(ledger["opponent_slots"][0]["status"], case["expected"])


def test_request_fixtures_preserve_forced_switch_and_wait_types():
    cases = {case["id"]: case for case in _cases()["cases"]}
    forced = cases["forced_switch_request"]
    forced_meta = extract_request_metadata(
        SimpleNamespace(
            last_request=forced["observed_inputs"],
            turn=2,
            battle_tag="battle-1",
            force_switch=False,
            wait=False,
            trapped=False,
            maybe_trapped=False,
        ),
        state_version=2,
    )
    assert forced_meta.request_type == forced["expected"]["value"]
    assert forced_meta.force_switch is True

    waited = cases["wait_request"]
    wait_meta = extract_request_metadata(
        SimpleNamespace(
            last_request={},
            turn=2,
            battle_tag="battle-1",
            force_switch=False,
            wait=waited["observed_inputs"]["wait"],
            trapped=False,
            maybe_trapped=False,
        ),
        state_version=2,
    )
    assert wait_meta.request_type == waited["expected"]["value"]


def test_wait_and_tera_fixtures_map_only_exact_legal_orders():
    cases = {case["id"]: case for case in _cases()["cases"]}
    wait_candidate = build_candidate_actions(
        SimpleNamespace(valid_orders=[DefaultBattleOrder()])
    )["default"]
    assert wait_candidate.kind == cases["wait_request"]["expected"]["value"] or wait_candidate.kind == "default"

    tera_case = cases["tera_move"]
    move = Move(tera_case["observed_inputs"]["move_id"], 9)
    tera_order = SingleBattleOrder(move, terastallize=True)
    tera_candidate = build_candidate_actions(SimpleNamespace(valid_orders=[tera_order]))
    only_candidate = next(iter(tera_candidate.values()))
    assert only_candidate.kind == tera_case["expected"]["value"]


def test_incomplete_opponent_state_never_claims_exact_damage():
    candidate = _fact_candidate()
    battle = SimpleNamespace(opponent_active_pokemon=None)

    annotate_candidates_with_facts(battle, {candidate.id: candidate})

    assert candidate.facts["damage"]["source"] in {"unknown", "inferred"}
    assert candidate.facts["damage"]["source"] != "calculated"
    assert candidate.facts["ko"]["value"] is None
