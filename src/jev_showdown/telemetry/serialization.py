"""Strict JSON-safe normalization for battle telemetry and audit records."""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


def _qualified_type(value: Any) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _mapping_key(value: Any) -> str:
    normalized = json_safe(value)
    if isinstance(normalized, str):
        return normalized
    if normalized is None or isinstance(normalized, (bool, int, float)):
        return str(normalized)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, allow_nan=False)


def json_safe(value: Any) -> Any:
    """Return a JSON-compatible representation without exposing object reprs.

    The battle snapshot already uses this representation for Jev input. The
    same boundary must also be applied to telemetry because raw beliefs and
    consequences can still contain poke-env enums such as ``PokemonType``.
    Unknown objects are represented by their qualified type only; their repr
    is intentionally excluded so telemetry cannot leak object internals or
    credentials.
    """
    if isinstance(value, Enum):
        return value.name
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {
            _mapping_key(key): json_safe(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [json_safe(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        try:
            return json_safe(asdict(value))
        except Exception:
            pass
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    return {"__type__": _qualified_type(value)}
