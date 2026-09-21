# Foul Play Post-History-Fix Evaluation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to execute this evaluation task-by-task. Do not spawn subagents.

**Goal:** Measure the current Jev harness after battle-history isolation against the fixed timer-safe Foul Play configuration using one fully audited three-battle series.

**Architecture:** Run the existing production `JevPlayer` headlessly against the pinned local Showdown engine and pinned Foul Play checkout. Reuse the already calibrated `10000 ms` Foul Play search configuration and the existing artifact runner, placing all new records in a fresh directory. Stop on the first protocol, provider, fallback, illegal-action, stale-response, or timer failure; never retry or escalate.

**Tech Stack:** Python 3, existing project virtual environment, `poke-env`, Jev API, local Pokémon Showdown, pinned Foul Play, `gen9randombattle`.

**Spec:** `docs/superpowers/plans/2026-09-21-per-battle-history-isolation.md` and `docs/superpowers/plans/2026-09-21-foul-play-max-strength-three-battle-evaluation.md`.

## Global Constraints

- Use exactly one fresh series of at most three battles; do not automatically repeat it.
- Use Foul Play search `10000 ms`, search parallelism `4`, team-preview search `10000 ms`, team-preview parallelism `4`, and one search thread.
- Make one Jev provider request per decision with no retries.
- Do not run dashboard UI, shadow battles, PokeChamp, or search-budget escalation.
- Preserve redacted Jev requests/responses, event records, Foul Play logs, Showdown logs, process metadata, and final outcomes.
- Do not persist credentials or authorization headers.
- This run measures the post-history-fix implementation; it cannot prove long-run superiority from three battles.

## Review Focus

- The new battle must start with no previous battle history: inspect the first request of each battle.
- Every Jev call must have a matching request/response record and decision event.
- No fallback or telemetry exception may prevent order submission.
- Foul Play must submit within the local Showdown timer.
- All processes must be terminated and the port released after the run.

### Task 1: Prepare and freeze the fresh audit directory

**Files:**
- Create: `artifacts/foul-play-evaluation-post-history-fix-10s-2026-09-21/`
- Create: `evaluation-config.json`, `process-commands.json`, process/log/audit files inside that directory.
- Reuse: `artifacts/foul-play-evaluation-2026-09-21/run_jev_agent.py` and `run_foul_play_local.py` without modifying source code.

- [x] **Step 1: Run provider-free gates before spending Jev calls**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass before any evaluation process starts.

- [x] **Step 2: Write the frozen configuration and start records**

Record the exact pinned commits, format, server URL, timing values, model, one-call policy, and fresh artifact path. Do not print or persist credentials.

### Task 2: Run the one fresh series

- [x] **Step 1: Start local Showdown**

Start the official local checkout with `node pokemon-showdown start --skip-build --no-security 8001` and save stdout/stderr.

- [x] **Step 2: Start the Jev runner**

Use `JEV_EVAL_ARTIFACT_DIR` and `JEV_EVAL_SHOWDOWN_SERVER_URL=ws://localhost:8001/showdown/websocket`; save stdout/stderr and the runner PID.

- [x] **Step 3: Start Foul Play once**

Run the pinned local Foul Play command with `FoulFix`, `gen9randombattle`, the frozen timing values, `--run-count 3`, and `--save-replay always`; save stdout/stderr and all bot logs.

- [x] **Step 4: Classify invalid conditions and complete cleanup**

The existing ladder runner does not expose a per-battle early-stop callback. The run was therefore classified invalid when fallbacks appeared, allowed the already-started three-battle process to finish for complete evidence, and performed no retry or additional paid run.

### Task 3: Audit and report

- [x] **Step 1: Validate request/event completeness and current-battle history**

Parse every JSONL line, compare Jev calls with decisions, scan for credentials, and verify each battle's first snapshot has no cards from an earlier battle tag.

- [x] **Step 2: Write the authoritative `final-audit.json`**

Include exact configuration, battle results, Jev calls, latency percentiles, fallbacks/errors, artifact paths, process cleanup, and limitations.

- [x] **Step 3: Run final provider-free verification and cleanup checks**

Run the full pytest suite again, verify port 8001 is free, verify no evaluation processes remain, and record whether the result supports the competitive hypothesis.

## Completion Criteria

- [x] All provider-free gates pass before and after the run.
- [x] The fresh series has exactly three battles and no automatic retry.
- [x] All audit records are parseable and credential-free.
- [x] The post-history-fix first-request audit passes.
- [x] Jev API usage is exactly the one series required for this measurement.
- [x] The conclusion distinguishes a three-battle sample from proof of superiority.

## Execution Result (2026-09-21)

The fresh series completed three battles at the frozen timer-safe configuration. Jev made 77 calls for 77 decisions; Foul Play won all three battles (turns 21, 19, and 22). The run produced 20 deterministic fallbacks: 14 provider HTTP 503 errors, 5 request timeouts, and 1 materially invalid probability response. There were 0 illegal actions, 0 stale responses, and 0 Showdown timer failures. Latency was p50 `1136.9263 ms`, p95 `10059.9752 ms`, and p99 `10465.1699 ms`.

The live history-isolation audit passed: each battle's first Jev snapshot contained only its own turn-1 opponent switch and no cards from earlier battle tags. However, because 20 decisions used fallback rather than valid Jev output, this series is invalid for strategic comparison and does not establish that Jev beats Foul Play. The authoritative audit is `artifacts/foul-play-evaluation-post-history-fix-10s-2026-09-21/final-audit.json`.

No retry, additional series, search escalation, shadow battle, dashboard run, or PokeChamp run was started. A provider-free floating-point boundary correction was then made and verified separately (`108 passed, 2 warnings`); no further Jev calls were spent.
