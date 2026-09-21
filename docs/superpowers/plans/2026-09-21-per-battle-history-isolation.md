# Per-Battle History Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent recent battle history from leaking between simultaneous or sequential Showdown battles before it is sent to Jev.

**Architecture:** Keep the existing compact `TurnHistoryTracker` data shape, but scope tracker instances by battle tag. The existing public `history_tracker` remains the initial/default tracker for backward compatibility with current callers and tests; live decision, scanner, and telemetry paths resolve the tracker for the current battle. Finished battle trackers are removed after scanner flush and `BATTLE_END` emission.

**Tech Stack:** Python 3, `poke-env`, pytest, existing Jev snapshot/telemetry pipeline.

**Spec:** Offline remediation discovered during `artifacts/foul-play-evaluation-after-probability-fix-10s-2026-09-21` audit.

## Global Constraints

- Do not make any additional Jev API calls for this remediation.
- Do not change legal-action generation, Pokémon strategy rules, or Jev response semantics.
- Preserve complete raw request/response/event audit records.
- Do not hard-code a Pokémon strategy or prune legal actions.
- Preserve the existing public `history_tracker` compatibility behavior for the first/default tracker.

## Review Focus

- A new battle must not receive the previous battle's recent-history cards: regression test in `tests/unit/test_agent.py`.
- Scanner events must merge with the current battle's decision card rather than another battle's card: existing scanner tests plus focused suite.
- Finished battle scanner flush must occur before its tracker is discarded: existing lifecycle/scanner behavior plus focused suite.
- Existing callers that inspect or inject `player.history_tracker` must continue to work: existing agent tests.
- Concurrent battle tags must have independent history even when turns use the same numeric turn: regression test uses distinct tags and same turn number.

### Task 1: Add the failing cross-battle regression test

**Files:**
- Modify: `tests/unit/test_agent.py`
- Read: `src/jev_showdown/agent.py`

**Interfaces:**
- Consumes: `JevPlayer.choose_move`, `_battle_finished_callback`, and the Jev client test double already used in this file.
- Produces: A reproducible failing test proving `state["recent_history"]` is isolated by battle tag.

- [x] **Step 1: Write the failing test**

Add an async test that creates battle tag A and battle tag B with the same turn number, lets Jev choose once in A, finishes A, then lets Jev choose once in B. Assert the second Jev request has an empty `recent_history` and does not contain A's action.

- [x] **Step 2: Run the test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_agent.py::test_recent_history_isolated_between_battles -q
```

Expected before the production change: FAIL because battle B receives battle A's decision card.

### Task 2: Scope trackers by battle tag with the smallest production change

**Files:**
- Modify: `src/jev_showdown/agent.py:119-121, 162-168, 350-357, 455-486, 567-599`
- Test: `tests/unit/test_agent.py`

**Interfaces:**
- Consumes: `_battle_key`, `TurnHistoryTracker`, scanner events, and existing lifecycle callbacks.
- Produces: `_history_trackers: dict[str, TurnHistoryTracker]` and a private resolver used by decision, scanner merge, and telemetry paths.

- [x] **Step 1: Add per-battle tracker resolution**

Initialize a tracker map. Resolve the first encountered battle key to the injected/default public tracker, then create a fresh tracker for every additional battle key. Use the resolver in `choose_move`, decision recording, telemetry history, and `_merge_scanner_event`.

- [x] **Step 2: Remove a tracker only after final scanner flush**

In `_battle_finished_callback`, flush the tag's scanner through the tag-scoped tracker, emit `BATTLE_END`, then remove that tag's tracker. Do not clear another battle's tracker.

- [x] **Step 3: Run focused tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_agent.py tests/unit/test_snapshot_and_telemetry.py -q
```

Expected: all focused tests pass, including the new isolation regression.

### Task 3: Provider-free verification and audit documentation

**Files:**
- Modify: `.superpowers/sdd/jev-probability-rounding-fix/progress.md`
- Modify: `docs/superpowers/plans/2026-09-21-jev-probability-rounding-fix.md`
- Modify: `docs/superpowers/plans/2026-09-21-foul-play-max-strength-three-battle-evaluation.md`
- Modify: `.superpowers/sdd/foul-play-max-strength-three-battle-evaluation/remediation-todo.md`

**Interfaces:**
- Consumes: focused test result, full pytest result, and existing paid evaluation artifact.
- Produces: an explicit record that the paid 1–2 series was not rerun after this offline fix and that no new Jev calls were spent.

- [x] **Step 1: Run the complete provider-free suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: exit code 0 with all tests passing and no new paid-provider activity.

- [x] **Step 2: Review the diff and audit scope**

Run `git diff --check`, inspect changed source/tests/docs, and verify no evaluation process or Showdown listener remains from the earlier run.

- [x] **Step 3: Record the result**

Document the leak, the fix, fresh test evidence, and the decision not to spend another Jev call. Do not claim that Jev has beaten Foul Play; a clean post-fix paid retest remains the measurement needed for that claim.

## Completion Criteria

- [x] The regression test fails before the fix and passes after it.
- [x] Current-battle history is the only history placed in a Jev snapshot.
- [x] Existing telemetry/scanner behavior remains green.
- [x] Full provider-free suite passes.
- [x] No additional Jev API calls are made for this remediation.
- [x] Documentation states the exact current Foul Play result and remaining evaluation limitation.

## Execution Result (2026-09-21)

The red test first failed because battle B received battle A's Earthquake history card. The implementation then introduced battle-tag-scoped trackers, kept the injected/default public tracker for the first battle for compatibility, flushed scanner events before cleanup, and removed the finished battle's tracker after `BATTLE_END` emission. The focused agent/telemetry suite passed with `18 passed`; the full provider-free suite passed with `107 passed, 2 warnings`.

No Jev API calls were made for this remediation. The existing paid series remains `1` win / `2` losses from 74 calls and was not rerun; this fix therefore improves harness correctness but does not by itself establish that Jev beats Foul Play.

The scoped source/test diff check was clean. The repository-wide `git diff --check` still reports the pre-existing `docs/superpowers/plans/2026-09-21-jev-harness-redesign.md:746` blank-line warning and normal Windows LF-to-CRLF warnings; no new whitespace error was introduced by this remediation. Port 8001 was free and no evaluation/Showdown process remained.
