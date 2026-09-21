import json
from dataclasses import dataclass

from poke_env.battle import PokemonType

from jev_showdown.telemetry.serialization import json_safe


@dataclass
class _Facts:
    attack_type: object


def test_json_safe_normalizes_pokemon_type_and_nested_telemetry():
    payload = {
        "beliefs": {"tera_type": PokemonType.FIRE},
        "facts": _Facts(attack_type=PokemonType.WATER),
    }

    normalized = json_safe(payload)

    assert normalized["beliefs"]["tera_type"] == "FIRE"
    assert normalized["facts"]["attack_type"] == "WATER"
    json.dumps(normalized, allow_nan=False)


def test_json_safe_marks_unknown_objects_without_exposing_object_repr():
    secret_object = object()

    normalized = json_safe({"value": secret_object})

    assert normalized["value"]["__type__"] == "builtins.object"
    assert "object at" not in json.dumps(normalized)
    json.dumps(normalized, allow_nan=False)
