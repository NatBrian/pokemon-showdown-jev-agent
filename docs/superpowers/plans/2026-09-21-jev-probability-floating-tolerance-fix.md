# Jev Probability Floating-Point Tolerance Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. No subagents and no Jev API calls.

**Goal:** Accept complete provider probability vectors whose decimal sum is exactly within the configured `0.01` rounding tolerance, even when binary floating-point representation is a few ulps above the boundary.

**Architecture:** Keep the existing narrow tolerance and structural validation. Add only a tiny numerical margin to the comparison or use a numerically stable closeness check; do not widen the meaningful acceptance range or alter action selection.

**Tech Stack:** Python 3, pytest, existing Jev protocol validator.

**Spec:** Offline evidence from call 30 in `artifacts/foul-play-evaluation-post-history-fix-10s-2026-09-21/jev-request-response.jsonl`.

## Global Constraints

- No Jev API calls.
- Preserve rejection of materially invalid totals, missing IDs, and all-zero probability maps.
- Preserve raw provider responses in audit records.
- Do not change legal-action generation or strategy logic.

### Task 1: Reproduce and fix the floating-point boundary

**Files:**
- Modify: `tests/unit/test_jev_client.py`
- Modify: `src/jev_showdown/decision/protocol.py`

- [x] **Step 1: Add the exact call-30 regression test**

Assert that a complete nine-entry two-decimal probability vector with a mathematical sum of `0.99` is accepted and normalized, including the floating-point ordering that produces `0.9899999999999999`; call 30 remains the production evidence that exposed the boundary.

- [x] **Step 2: Run the test and observe the expected boundary failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_jev_client.py::test_jev_client_accepts_exact_decimal_rounding_boundary -q
```

Expected before the fix: failure with `probability sum must equal 1.0`.

- [x] **Step 3: Make the smallest numerical comparison fix**

Retain `PROBABILITY_SUM_TOLERANCE = 0.01`, but make the comparison robust to floating-point ulps without accepting a total beyond the intended decimal boundary.

- [x] **Step 4: Run focused and full provider-free tests**

Run the focused Jev client suite and then `pytest -q`; no provider request is permitted.

## Completion Criteria

- [x] The exact decimal rounding boundary is accepted; the saved call-30 evidence remains replayable.
- [x] Existing invalid-vector tests remain green.
- [x] Full provider-free suite passes.
- [x] No Jev API calls are made.

## Execution Result (2026-09-21)

The initial call-30 replay with its displayed decimal ordering passed, so it was not a deterministic regression by itself. A mathematically equivalent two-decimal vector that sums to `0.99` but produces a binary float total of `0.9899999999999999` reproduced the exact validator failure. The fix keeps `PROBABILITY_SUM_TOLERANCE = 0.01` and adds only `PROBABILITY_SUM_NUMERIC_EPSILON = 1e-12` to the comparison boundary.

The regression test failed before the production change and passed after it. Focused Jev client/agent/fallback tests passed with `26 passed`; the full provider-free suite passed with `108 passed, 2 warnings`. No Jev API call was made.
