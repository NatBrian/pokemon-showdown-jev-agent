from unittest.mock import MagicMock

from poke_env.battle import Move, Pokemon
from poke_env.player.battle_order import DefaultBattleOrder, SingleBattleOrder

from jev_showdown.battle.candidates import build_candidate_actions


def _battle(orders, **flags):
    battle = MagicMock()
    battle.valid_orders = orders
    battle.force_switch = flags.get("force_switch", False)
    battle.wait = flags.get("wait", False)
    return battle


def test_candidate_registry_preserves_every_legal_order_message_in_order():
    move = Move("earthquake", 9)
    switch = Pokemon(9, species="Rotom-Wash", name="rotomwash")
    tera_move = Move("earthquake", 9)
    orders = [
        SingleBattleOrder(move),
        SingleBattleOrder(switch),
        SingleBattleOrder(tera_move, terastallize=True),
    ]

    candidates = build_candidate_actions(_battle(orders))

    assert [candidate.order_ref.message for candidate in candidates.values()] == [
        order.message for order in orders
    ]
    assert list(candidates) == [
        "move_earthquake",
        "switch_rotomwash",
        "move_earthquake_tera",
    ]
    assert candidates["move_earthquake_tera"].kind == "move_tera"


def test_forced_switch_registry_contains_only_the_current_switch_orders():
    switch = Pokemon(9, species="Rotom-Wash", name="rotomwash")
    order = SingleBattleOrder(switch)

    candidates = build_candidate_actions(_battle([order], force_switch=True))

    assert list(candidates) == ["switch_rotomwash"]
    assert candidates["switch_rotomwash"].order_ref is order


def test_wait_registry_represents_the_default_order():
    order = DefaultBattleOrder()

    candidates = build_candidate_actions(_battle([order], wait=True))

    assert list(candidates) == ["default"]
    assert candidates["default"].kind == "default"
    assert candidates["default"].order_ref is order
    assert candidates["default"].order_ref.message == "/choose default"


def test_duplicate_move_and_switch_ids_are_disambiguated_without_losing_orders():
    first_move = Move("tackle", 9)
    second_move = Move("tackle", 9)
    first_switch = Pokemon(9, species="Rotom", name="rotom")
    second_switch = Pokemon(9, species="Rotom", name="rotom")
    orders = [
        SingleBattleOrder(first_move),
        SingleBattleOrder(second_move),
        SingleBattleOrder(first_switch),
        SingleBattleOrder(second_switch),
    ]

    candidates = build_candidate_actions(_battle(orders))

    assert list(candidates) == [
        "move_tackle",
        "move_tackle_2",
        "switch_rotom",
        "switch_rotom_2",
    ]
    assert [candidate.order_ref for candidate in candidates.values()] == orders


def test_tera_action_is_not_invented_when_only_the_normal_order_is_legal():
    move = Move("earthquake", 9)
    order = SingleBattleOrder(move)

    candidates = build_candidate_actions(_battle([order]))

    assert list(candidates) == ["move_earthquake"]
    assert all(not candidate.kind.endswith("tera") for candidate in candidates.values())
