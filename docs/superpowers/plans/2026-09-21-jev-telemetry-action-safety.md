# Jev Telemetry and Action Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure telemetry, audit serialization, and malformed Jev responses can never prevent the Jev player from submitting a legal Pokémon action.

**Architecture:** Add one shared primitive normalization boundary for telemetry and JSONL records. `JevPlayer` will normalize events before dispatch and isolate callback failures from the decision path, while the evaluation writer will serialize a complete line before opening the file. Existing legal-action validation and deterministic fallback remain the authority for submitted orders.

**Tech Stack:** Python 3.10+, `poke-env`, `pytest`, `pytest-asyncio`, standard-library `json`, `enum`, and `dataclasses`.

**Spec:** `.superpowers/sdd/foul-play-max-strength-three-battle-evaluation/remediation-todo.md`

## Global Constraints

- Do not make any Jev API calls during implementation or provider-free verification.
- Do not prune legal Pokémon actions or change Jev candidate semantics.
- Telemetry failures must not block or alter a validated legal order.
- Preserve source/unit/confidence fields; normalization is representation-only.
- Preserve credential redaction in evaluation artifacts.
- Do not rerun Foul Play until all provider-free gates pass and the user authorizes another paid run.

## Review Focus

- `PokemonType`/enum values inside beliefs, consequences, or raw event fields must become stable JSON values; test with a real enum.
- A telemetry callback that raises must not prevent `choose_move` from returning its validated order; test with a raising callback.
- A malformed Jev probability response must still produce a legal deterministic fallback and an auditable event; test the existing validator path.
- A serialization failure must not leave a partial JSONL record; test pre-serialization and independent line parsing.
- Battle lifecycle and raw protocol callbacks must remain non-fatal and JSON-safe; test their error isolation.

---

### Task 1: Shared JSON-safe telemetry boundary

**Files:**
- Create: `src/jev_showdown/telemetry/serialization.py`
- Modify: `src/jev_showdown/battle/snapshot.py`
- Create: `tests/unit/test_telemetry_serialization.py`

**Interfaces:**
- Consumes: arbitrary telemetry values, including mappings, sequences, sets, enum-like values, and dataclass values.
- Produces: `json_safe(value: Any) -> Any`, returning only JSON-compatible primitives, lists, and string-keyed dictionaries; unknown objects become a tagged type marker instead of raising.

- [ ] **Step 1: Write failing tests**

  Add tests that use a real `enum.Enum` value and a nested event containing it, assert `json.dumps(json_safe(event), allow_nan=False)` succeeds, assert the enum becomes its stable name, and assert an unknown object becomes a tagged marker without raising. Add a test that existing snapshot normalization still produces the same primitive type strings.

- [ ] **Step 2: Run the focused tests and confirm the expected failure**

  Run: `python -m pytest tests/unit/test_telemetry_serialization.py -q`

  Expected: FAIL because `jev_showdown.telemetry.serialization` and `json_safe` do not yet exist.

- [ ] **Step 3: Implement the minimal normalization boundary**

  Implement recursion for `None`, booleans, numbers, strings, mappings, lists/tuples/sets, enums, dataclasses, and enum-like `.name` values. Convert mapping keys to stable strings. For an unsupported object, return a tagged dictionary containing its qualified type name and no object representation. Replace the private snapshot helper with this shared function without changing snapshot output.

- [ ] **Step 4: Run focused and existing snapshot tests**

  Run: `python -m pytest tests/unit/test_telemetry_serialization.py tests/unit/test_snapshot_and_telemetry.py -q`

  Expected: all tests pass and serialized snapshots remain JSON-compatible.

### Task 2: Non-fatal JevPlayer telemetry dispatch

**Files:**
- Modify: `src/jev_showdown/agent.py`
- Modify: `src/jev_showdown/main.py`
- Modify: `tests/unit/test_agent.py`
- Modify: `tests/unit/test_orchestrator.py`

**Interfaces:**
- Consumes: `json_safe` from Task 1 and existing `on_turn_event`, `on_battle_event`, and `on_battle_frame` callbacks.
- Produces: optional `on_telemetry_error` callback, normalized callback payloads, and a `telemetry_errors` in-memory list for diagnostics; callback errors never escape the battle decision path.

- [ ] **Step 1: Write failing tests**

  Add an async test that supplies a real enum-like value in the event source and a turn callback that raises; assert `choose_move` returns a `BattleOrder`, the callback received a JSON-safe event before raising, and a `TELEMETRY_ERROR` diagnostic is emitted to the separate error callback/list. Add tests that lifecycle and frame callbacks raising do not raise from `_create_battle` or `_handle_battle_message`.

- [ ] **Step 2: Run the focused tests and confirm the expected failure**

  Run: `python -m pytest tests/unit/test_agent.py -q`

  Expected: FAIL because turn callback exceptions currently escape `choose_move` and no telemetry-error channel exists.

- [ ] **Step 3: Implement the minimal safe dispatch**

  Add a private dispatch helper that normalizes the event, invokes the callback inside `try/except`, records a safe diagnostic, and invokes the optional error callback without allowing a second callback failure to escape. Normalize turn, lifecycle, and frame payloads. Wrap the `_record_turn` invocation in `choose_move` so an internal telemetry failure cannot block the return of `validated.order`. Keep action resolution and fallback logic unchanged.

- [ ] **Step 4: Run focused tests and the existing agent suite**

  Run: `python -m pytest tests/unit/test_agent.py tests/unit/test_live_protocol_scanner.py -q`

  Expected: all tests pass, including the new callback-failure tests, with no action-validation regressions.

### Task 3: Atomic audit JSONL recording

**Files:**
- Create: `src/jev_showdown/telemetry/recording.py`
- Modify: `artifacts/foul-play-evaluation-2026-09-21/run_jev_agent.py`
- Create: `tests/unit/test_telemetry_recording.py`

**Interfaces:**
- Consumes: redacted event dictionaries from the evaluation runner.
- Produces: `encode_json_line(value: Any) -> str` and `append_jsonl(path: Path, value: Any) -> None`; encoding completes before the file is opened, and each successful append is one independently parseable line.

- [ ] **Step 1: Write failing tests**

  Add tests that encode an event containing an enum and an unsupported object, parse the returned line with `json.loads`, and append two records to a temporary file then parse each line independently. Add a failure test using a value whose normalization raises and assert the target file is unchanged.

- [ ] **Step 2: Run the focused tests and confirm the expected failure**

  Run: `python -m pytest tests/unit/test_telemetry_recording.py -q`

  Expected: FAIL because the recording module and functions do not yet exist.

- [ ] **Step 3: Implement atomic pre-serialization and update the evaluation runner**

  Implement `encode_json_line` using `json_safe`, `json.dumps`, `ensure_ascii=False`, `sort_keys=True`, and strict JSON output. Implement `append_jsonl` by encoding before opening the path and writing the complete payload plus one newline. Update the evaluation runner to redact first and call the shared writer; pass `on_telemetry_error` to the player so recording errors are retained without interrupting decisions.

- [ ] **Step 4: Run focused recording and runner-import tests**

  Run: `python -m pytest tests/unit/test_telemetry_recording.py -q`

  Expected: all tests pass and every written line parses independently.

### Task 4: Malformed-response and provider-free battle verification

**Files:**
- Modify: `tests/unit/test_agent.py`
- Modify: `tests/integration/test_e2e_battle.py` only if the existing provider-free harness needs an assertion for telemetry errors.
- Modify: `.superpowers/sdd/foul-play-max-strength-three-battle-evaluation/remediation-todo.md`

**Interfaces:**
- Consumes: completed safe telemetry and recording behavior from Tasks 1–3.
- Produces: evidence that legal action submission, fallback, telemetry validity, and provider-free battle completion work together.

- [ ] **Step 1: Add the malformed-probability regression test**

  Feed a Jev response whose probability sum is invalid through the existing decision path and assert the returned order is legal, `is_fallback` is true, and the event records the error without callback failure.

- [ ] **Step 2: Run the new regression test and confirm it fails for the original reason**

  Run: `python -m pytest tests/unit/test_agent.py -k "probability or telemetry" -q`

  Expected: the new callback/recording regression fails before the implementation and identifies the unsafe telemetry path rather than a test setup error.

- [ ] **Step 3: Run the complete provider-free suite**

  Run: `python -m pytest -q`

  Expected: all tests pass; no Jev network call is made by the suite.

- [ ] **Step 4: Run the provider-free simulated battle smoke**

  Run the existing RandomPlayer and SimpleHeuristicsPlayer simulations/replay smoke commands from the benchmark harness. Confirm no inactivity, illegal action, stale action, or provider error; confirm all emitted event records are JSON-parseable and the provider call count is zero.

- [ ] **Step 5: Update the remediation checklist with evidence**

  Mark only verified items complete, record the exact test commands and counts, and leave the paid evaluation gate open until the user explicitly authorizes a new paid Foul Play run.

## Completion Gate

The remediation is complete only when the full provider-free suite and provider-free battle smoke pass, the saved event/recording tests prove JSONL integrity, and no Jev API call has been made after the invalid Foul Play run. A new paid Foul Play evaluation is a separate user-approved action.
