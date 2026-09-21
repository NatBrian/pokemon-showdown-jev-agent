import json
from enum import Enum

import pytest

from jev_showdown.telemetry import recording
from jev_showdown.telemetry.recording import append_jsonl, encode_json_line


class _Kind(Enum):
    OBSERVED = "observed"


def test_encode_json_line_returns_strict_parseable_json():
    line = encode_json_line({"kind": _Kind.OBSERVED, "values": [1, None, True]})

    assert json.loads(line) == {
        "kind": "OBSERVED",
        "values": [1, None, True],
    }


def test_append_jsonl_writes_independently_parseable_records(tmp_path):
    path = tmp_path / "events.jsonl"

    append_jsonl(path, {"id": 1})
    append_jsonl(path, {"id": 2})

    assert [json.loads(line) for line in path.read_text().splitlines()] == [
        {"id": 1},
        {"id": 2},
    ]


def test_append_jsonl_serializes_before_opening_file(tmp_path, monkeypatch):
    path = tmp_path / "events.jsonl"
    path.write_text('{"existing":true}\n', encoding="utf-8")

    def fail_dump(*args, **kwargs):
        raise ValueError("serialization failed")

    monkeypatch.setattr(recording.json, "dumps", fail_dump)

    with pytest.raises(ValueError, match="serialization failed"):
        append_jsonl(path, {"new": True})

    assert path.read_text(encoding="utf-8") == '{"existing":true}\n'
