# Foul Play Maximum-Strength Three-Battle Evaluation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to execute this evaluation task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not spawn subagents.

**Goal:** Evaluate the merged Jev Pokémon Showdown agent against Foul Play once, at the strongest practical fixed search configuration, using exactly three local battles.

**Architecture:** Run Foul Play and the Jev agent as separate clients against the official local Showdown engine. Use the same headless `JevPlayer` production decision path and telemetry used by the application; do not require the dashboard UI for this benchmark. Treat the series as a bounded engineering and strength signal, not an Elo estimate.

**Tech Stack:** Foul Play, local Pokémon Showdown server, `poke-env`, `JevSystemOneClient`, `gen9randombattle`, existing telemetry and benchmark metrics.

**Spec:** `docs/superpowers/plans/2026-09-21-jev-harness-redesign.md`, section “Foul Play Evaluation Handoff (After Implementation)”.

## Global Constraints

- Run exactly one series of three battles; do not automatically repeat it.
- Use `gen9randombattle` unless the discovered Foul Play integration requires an explicitly documented equivalent format.
- Use the strongest practical fixed Foul Play configuration selected before battle 1.
- “Strongest practical” means the highest search setting that can reliably make legal decisions within the Showdown battle timer on this machine; do not use an unbounded search that turns the run into a timeout test.
- Do not increase Foul Play search budget between battles.
- Make one Jev API request per decision; do not add retries, shadow battles, or extra paid audit calls.
- Run headlessly through `JevPlayer`; dashboard rendering is a separate smoke-test concern and is not part of this benchmark.
- Do not run PokeChamp.
- Do not import or modify Foul Play source inside `src/jev_showdown`.
- Persist complete local audit artifacts for every battle: Foul Play stdout/stderr and log files, Showdown server logs, Jev request payloads, Jev raw responses, timestamps, latency, validation/fallback telemetry, process metadata, and final outcomes.
- Redact authorization headers, API tokens, passwords, and other credentials from persisted artifacts; do not discard the decision state, criteria, response body, or error details needed to audit a paid Jev call.
- Stop the series on protocol failure, illegal order, stale submission, repeated provider failure, or unacceptable latency; record the stop reason and do not silently restart.

## Decisions Already Made

- The user rejected automatic search-budget escalation to protect Jev API cost.
- The user approved three battles as the maximum first series.
- The user approved maximum practical Foul Play strength rather than a weak pilot opponent.
- The user approved headless evaluation instead of requiring the unfinished dashboard.
- The user accepted skipping additional synthetic audit-corpus calls; the Foul Play series is the first full end-to-end evaluation. Cost if wrong: a scenario-specific harness issue may be discovered later than it would have been by a richer pre-audit.

## Progress Checklist

- [x] Merge the harness redesign into `master`.
- [x] Run the merged no-provider suite: 93 passed, 2 existing dependency warnings.
- [x] Run provider-free local RandomPlayer and SimpleHeuristicsPlayer gates: one simulated battle each, 0 fallbacks, 0 illegal actions, 0 stale responses.
- [x] Run the limited Jev smoke audit: 4 Jev calls total, 3 legal responses and 1 transient error; the failed position reproduced successfully once.
- [x] Locate the Foul Play checkout and local Showdown checkout without changing project code.
- [x] Record the exact Foul Play commit, Showdown commit/version, runtime entrypoint, format, and available search/parallelism/thread controls.
- [x] Select and record one fixed Foul Play candidate before starting battle 1. Post-run validation found that the candidate was not timer-safe; see the final result below.
- [x] Confirm the Jev endpoint/model configuration without printing credentials or adding test calls.
- [x] Run exactly three headless battles against Foul Play. All three completed as server-recorded Foul Play inactivity forfeits.
- [x] Collect and validate battle outcomes, Jev call count, decision latency, fallbacks, illegal actions, stale responses, provider errors, timer outcomes, and complete redacted request/response/log artifacts.
- [x] Write the final evaluation result and limitations into this plan without claiming an Elo estimate.

## Task 1: Discover and Freeze the Evaluation Configuration

- [x] Inspect only the Foul Play and Showdown source/configuration needed to identify their runnable entrypoints and version identifiers.
- [x] Verify that both clients can connect to the same local Showdown server without starting a battle or making a Jev request.
- [ ] Determine the highest Foul Play search setting that remains compatible with the Showdown timer on this machine. The frozen 30000 ms candidate was later shown to be timer-unsafe, and no additional paid series or tuning run is permitted by this plan.
- [x] Freeze the selected values before battle 1 in `artifacts/foul-play-evaluation-2026-09-21/evaluation-config.json`: Foul Play commit, Showdown version, format, search time, parallelism, thread count, and local server URL.

Frozen configuration: Foul Play commit `6c467c081e862fb321adb405355beb41aba8e226`; Showdown commit `9e317a666d9fd250f36f494778e843141f09bdba` / package `0.11.11`; `gen9randombattle`; search `30000 ms`; parallelism `4`; team-preview search `30000 ms` / parallelism `4`; search threads `1`; run count `3`; replay saving `always`. Port 8001 is used because port 8000 is occupied by the existing dashboard process. The offline Showdown checkout also uses `noguestsecurity=true` for guest login and `noipchecks=true` so two local clients can be matched from the same machine. Both clients logged in successfully in a no-battle smoke test with zero Jev calls; the later corrected clients entered search but same-IP protection prevented pairing until this local-only override was enabled.

## Task 2: Run the Single Three-Battle Series

- [x] Start the official local Showdown engine.
- [x] Start the Jev agent through the headless `JevPlayer` path.
- [x] Start Foul Play with the frozen fixed configuration.
- [x] Route each component's stdout/stderr and log files into a timestamped evaluation-artifact directory, and attach a redacted Jev request/response record to each decision event.
- [x] Run battles 1, 2, and 3 only.
- [x] Preserve raw outcome/telemetry artifacts outside source files and redact credentials without removing audit-relevant state or response data.
- [x] Record the stop-condition evidence. Foul Play timed out by inactivity in battle 1 and the ladder runner did not halt before it produced battles 2 and 3; this orchestration gap is documented and no further battle was started.

## Task 3: Analyze and Report

- [x] Verify that the number of completed battles is exactly three and document the Foul Play stop condition.
- [x] Calculate wins, losses, draws, and win rate, while labeling the result as a three-battle sample.
- [x] Report total Jev calls and calls per decision; do not infer cost from an assumed average turn count.
- [x] Report fallback, illegal, stale, provider-error, timeout, and latency metrics.
- [x] Verify that every Jev call has a matching timestamped request and response/error record, with no authorization header or secret leakage.
- [x] Report the exact fixed Foul Play search configuration and both engine/bot versions.
- [x] State whether the result supports, weakens, or fails to establish the hypothesis that the harness plus Jev can compete with Foul Play.
- [x] Do not run another series or tune search settings automatically.

## Stop Conditions

Stop before starting the next battle if any of these occur:

- An order is rejected as illegal.
- A Jev response is stale or cannot be validated and the deterministic fallback is used unexpectedly.
- A protocol, connection, or engine error prevents a clean battle result.
- Provider failures repeat or the Jev path exceeds the configured battle-time budget.
- Foul Play cannot make a legal decision within the Showdown timer.

## Required Final Record

The final record must contain:

```text
Foul Play commit:
Showdown commit/version:
Format:
Foul Play command:
Search time:
Parallelism:
Threads:
Requested battles: 3
Completed battles:
Wins / losses / draws:
Win rate (three-battle sample):
Jev calls:
Decisions:
Fallbacks:
Illegal actions:
Stale responses:
Provider errors:
Latency p50 / p95 / p99:
Timer failures:
Artifact directory:
Request/response records complete:
Conclusion:
Limitations:
```

## Final Result (2026-09-21)

The exact three-battle series completed, but it is invalid as a strategic strength comparison. Jev won all three server-recorded games 3-0 because FoulPlayEval lost each game by inactivity at turns 4, 5, and 3. The result therefore fails to establish that Jev can compete with Foul Play.

The Jev path made 12 decisions using exactly 12 API calls (one call per decision), with zero provider errors, fallbacks, illegal actions, or stale responses. Decision latency was p50 1250.750 ms, p95 1368.744 ms, and p99 1420.314 ms. Every call has a saved timestamped request payload, raw response/error field, and response metadata in `jev-request-response.jsonl`.

The fixed configuration was Foul Play commit `6c467c081e862fb321adb405355beb41aba8e226`, Showdown commit `9e317a666d9fd250f36f494778e843141f09bdba` / package `0.11.11`, `gen9randombattle`, 30000 ms search, parallelism 4, one search thread, and 30000 ms team-preview search. Foul Play's logs show that this candidate consumed the available timer and failed to submit a later legal order. The complete audit is in `artifacts/foul-play-evaluation-2026-09-21/final-audit.json`; raw logs and three Showdown replay files are in the same artifact directory.

The prior limited Jev smoke audit used 4 calls; this Foul Play series used 12, for 16 Jev calls across this evaluation work. Setup correction attempts and the connection smoke test used zero Jev calls. The response cost field for this run's `jev-1.13-free` calls was `0`; no price estimate is inferred here.

## Corrected Local Continuation (User-Authorized, 2026-09-21)

The user authorized continuing on the local machine after the first series was invalidated by Foul Play inactivity. Before any new Jev call, a separate no-cost calibration was run against `poke-env RandomPlayer` using the same local Showdown checkout and pinned Foul Play commit. The 30000 ms candidate failed by inactivity; a 15000 ms candidate also failed at the late-battle timer boundary; a 10000 ms candidate completed a normal 14-turn battle with no timer failure.

The corrected evaluation is one additional and final three-battle series using `gen9randombattle`, Foul Play search `10000 ms`, search parallelism `4`, team-preview search `10000 ms` / parallelism `4`, search threads `1`, and one Jev request per decision. It will use a fresh audit directory, preserve all redacted requests/responses/logs, and stop without retry if a protocol, validation, provider, or Foul Play timer failure occurs. No further search-budget tuning, extra series, shadow battle, dashboard run, or PokeChamp run is authorized by this continuation.

## Corrected Local Continuation Result (2026-09-21)

- [x] Completed the no-cost calibration and froze the timer-safe candidate at Foul Play search `10000 ms`, parallelism `4`, one search thread, and matching `10000 ms` team-preview search.
- [x] Started the one authorized paid three-battle continuation with the production headless Jev path and complete audit capture.
- [x] Stopped the exact evaluation process tree when Jev failed to submit a decision and Showdown entered the inactivity countdown; no retry, fourth battle, search escalation, shadow battle, dashboard run, or PokeChamp run was started.
- [x] Preserved the Jev request/response records, partial event log, Jev stderr, Foul Play stdout/stderr and per-battle logs, Showdown server logs, and the two available Showdown replays.
- [x] Wrote the authoritative audit to `artifacts/foul-play-evaluation-corrected-10s-2026-09-21/final-audit.json`.

The corrected run started three battles. Battles 23 and 24 ended as Foul Play wins by Jev inactivity forfeits at turns 3 and 13; battle 25 was started but stopped before an outcome. Therefore zero battles are valid strategic comparisons. The root cause was the evaluation recorder: `record_event` attempted to JSON-serialize a `PokemonType` object, raised `TypeError: Object of type PokemonType is not JSON serializable`, and escaped `choose_move`. The exception prevented poke-env from receiving Jev's next order. The run recorded 20 Jev request/response records, 19 choices, and one provider-response validation error (`probability sum must equal 1.0`); the response latency p50/p95/p99 was 1131.031/1391.331/1435.283 ms. The `jev-events.jsonl` file is retained but partially malformed because the recorder failed during `json.dump`; `jev-run.stderr.log` and the replays provide the authoritative failure evidence.

This result is invalid for judging Jev's strategic strength against Foul Play. The next engineering action is to make event/audit serialization total and non-fatal, then verify that fix with provider-free tests before requesting any further paid battle. The current user instruction authorizes no additional paid Foul Play run in this task.

Calibration record: `artifacts/foul-play-calibration-2026-09-21/calibration-summary.json`.

## Plan Self-Review

- The plan does not require dashboard rendering, so incomplete UI cannot block the battle-path evaluation.
- The plan fixes bot strength before the first battle, preventing post-hoc tuning or repeated paid evaluation.
- The plan records the exact versions and timing controls needed to reproduce the result.
- The plan separates protocol/harness failures from battle-strength results.
- The plan has no automatic retry, escalation, PokeChamp run, or hidden Jev call.

## Post-remediation Authorized Paid Attempt (2026-09-21)

The user later explicitly authorized one fresh attempt after the telemetry serialization fix and provider-free verification passed. This section records that execution without altering the historical invalid-run sections above; the later authorization superseded the earlier temporary hold on another paid run.

Configuration remained fixed at Foul Play commit `6c467c081e862fb321adb405355beb41aba8e226`, Showdown commit `9e317a666d9fd250f36f494778e843141f09bdba` / package `0.11.11`, `gen9randombattle`, 10000 ms search, parallelism 4, one search thread, and matching 10000 ms team-preview search. The run used the headless production `JevPlayer` path and a local Showdown server on port 8001 with the offline-only `--no-security` overrides.

The run started one battle (`battle-gen9randombattle-34`) and recorded seven Jev API calls and seven decisions. On turn 2, call 2 returned `Invalid Jev Choice response: probability sum must equal 1.0`; the harness selected and submitted the first legal deterministic fallback (`switch Mienshao`). Because an unvalidated Jev response caused fallback, the plan's explicit stop condition fired. The evaluation processes were terminated immediately after the stop record was written. No battle outcome was recorded, so wins/losses/draws and win rate are not applicable.

Audit summary:

```text
Requested battles: 3
Started battles: 1
Completed battles: 0
Jev calls: 7
Decisions: 7
Fallbacks: 1
Illegal actions: 0
Stale responses: 0
Provider validation errors: 1
Decision latency p50 / p95 / p99: 1099.7812 ms / 1363.4562 ms / 1432.179 ms
Request/response records: complete and parseable
Event records: complete and parseable
Credential scan: no authorization/token leakage found
Conclusion: invalid for strategic comparison; no competitive-strength conclusion is supported
```

The authoritative audit is `artifacts/foul-play-evaluation-final-10s-2026-09-21/final-audit.json`. It includes the redacted request/response JSONL, event JSONL, process metadata and process tree, Showdown/Foul Play stdout and stderr, copied bot/server logs, replay directory, and stop-condition evidence. No retry, fourth battle, search-budget escalation, shadow battle, dashboard run, or PokeChamp run was started.

## Final Protocol-Fix Evaluation (2026-09-21)

The Jev protocol was then fixed and tested provider-free. The fix accepts the observed two-decimal rounding case where a complete probability vector totals `0.99`, normalizes it to one, and continues rejecting materially wrong totals, missing IDs, and all-zero maps. The focused client/agent/fallback tests passed (`24 passed`), the saved call-2 response replay passed with `jev_api_calls: 0`, and the full suite passed (`106 passed, 2 warnings`).

One fresh fixed three-battle series was run after that gate. It completed all three battles at Foul Play search `10000 ms`, parallelism `4`, one search thread, and matching `10000 ms` team-preview search. Jev made 74 calls for 74 decisions; all three battles had clean protocol execution with 0 fallbacks, 0 provider errors, 0 illegal actions, and 0 stale responses. Jev won battle 46 and lost battles 45 and 47, giving a valid 1-2 result and a 33.33% three-battle sample win rate. Decision latency was p50 `1171.7814 ms`, p95 `1964.927885 ms`, and p99 `2407.074736 ms`.

## Post-evaluation Offline History-Isolation Remediation (2026-09-21)

The single post-fix measurement is tracked separately in `docs/superpowers/plans/2026-09-21-foul-play-post-history-fix-evaluation.md`.

A provider-free audit of the final series found a separate harness correctness defect: battle 47's first Jev snapshot contained two history cards from battle 46 followed by battle 47 turn-1 cards. `JevPlayer` used one global `TurnHistoryTracker` even though battle scanners were keyed by battle tag, and `_battle_finished_callback` did not clear the global history.

The fix is documented in `docs/superpowers/plans/2026-09-21-per-battle-history-isolation.md`. History is now resolved per battle tag; the first/default public tracker remains compatible with existing callers, scanner flush occurs before cleanup, and the completed battle tracker is removed after `BATTLE_END`. The regression test was observed failing before the fix and passing after it. Focused tests passed with `18 passed`; the full provider-free suite passed with `107 passed, 2 warnings`.

No Jev API calls were spent on this remediation, and the 74-call paid series was not rerun. Therefore the recorded `1-2` result does not measure the post-isolation implementation; it still does not establish that Jev beats Foul Play. No strategic hard-coding or action pruning was added.

This is the first valid strategic comparison after the telemetry and probability-protocol fixes. It shows that the harness can complete the live path reliably, but it does not show that Jev can beat Foul Play. The two losses must not be converted into hard-coded Pokémon rules from this three-battle sample; doing so would violate the project's overfitting constraint. The authoritative audit is `artifacts/foul-play-evaluation-after-probability-fix-10s-2026-09-21/final-audit.json`, with complete redacted request/response records, event telemetry, bot/server logs, process metadata, and replay-save evidence. No further paid run was started.
