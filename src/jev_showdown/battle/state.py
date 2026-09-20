"""Defensive extraction of Showdown request metadata from poke-env battles."""

from collections.abc import Mapping, Sequence
from typing import Any

from poke_env.battle import AbstractBattle

from jev_showdown.battle.contracts import BattleRequestMetadata


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _flag(value: Any) -> bool:
    """Read protocol flags without treating absent MagicMock attributes as true."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (list, tuple)):
        return any(item is True for item in value)
    return False


def _turn(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    return 0


def _has_active_actions(request: Mapping[str, Any]) -> bool:
    active = request.get("active")
    if not isinstance(active, Sequence) or isinstance(active, (str, bytes)):
        return False
    return any(
        isinstance(entry, Mapping)
        and any(key in entry for key in ("moves", "actions", "canTerastallize"))
        for entry in active
    )


def _has_team_preview(request: Mapping[str, Any]) -> bool:
    return any(
        key in request and request[key] is not None
        for key in ("teamPreview", "team_preview", "preview")
    )


def extract_request_metadata(
    battle: AbstractBattle,
    *,
    state_version: int,
    deadline_monotonic: float | None = None,
) -> BattleRequestMetadata:
    request = _mapping(getattr(battle, "last_request", None))

    wait = _flag(getattr(battle, "wait", False)) or _flag(request.get("wait"))
    force_switch = _flag(getattr(battle, "force_switch", False)) or _flag(
        request.get("forceSwitch")
    )
    trapped = _flag(getattr(battle, "trapped", False))
    maybe_trapped = _flag(getattr(battle, "maybe_trapped", False))

    if wait:
        request_type = "wait"
    elif force_switch:
        request_type = "switch"
    elif _has_active_actions(request):
        request_type = "move"
    elif _has_team_preview(request):
        request_type = "team_preview"
    else:
        request_type = "unknown"

    battle_tag = getattr(battle, "battle_tag", None)
    battle_id = battle_tag if isinstance(battle_tag, str) else None

    request_id = request.get("rqid")
    if request_id is not None and not isinstance(request_id, (str, int)):
        request_id = None

    return BattleRequestMetadata(
        battle_id=battle_id,
        request_id=request_id,
        state_version=state_version,
        turn=_turn(getattr(battle, "turn", None)),
        request_type=request_type,
        force_switch=force_switch,
        wait=wait,
        trapped=trapped,
        maybe_trapped=maybe_trapped,
        deadline_monotonic=deadline_monotonic,
    )
