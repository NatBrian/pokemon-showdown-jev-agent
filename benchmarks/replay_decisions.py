"""No-provider JSONL persistence for inspecting live Jev decisions."""

import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any


def write_decision_package(path: Path, event: Mapping[str, Any]) -> None:
    """Append one JSON-safe decision/lifecycle event to a UTF-8 JSONL file."""
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        json.dump(dict(event), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def read_decision_packages(path: Path) -> Iterator[dict[str, Any]]:
    """Yield decision events and reject malformed lines with their line number."""
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc.msg}"
                ) from exc
            if not isinstance(value, dict):
                raise ValueError(
                    f"Expected a JSON object on line {line_number}"
                )
            yield value
