"""Strict, append-only JSONL recording for telemetry artifacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jev_showdown.telemetry.serialization import json_safe


def encode_json_line(value: Any) -> str:
    """Normalize and encode one complete JSONL record before file I/O."""
    return json.dumps(
        json_safe(value),
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
    )


def append_jsonl(path: Path, value: Any) -> None:
    """Append one complete record, leaving the file untouched if encoding fails."""
    line = encode_json_line(value)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.write("\n")
