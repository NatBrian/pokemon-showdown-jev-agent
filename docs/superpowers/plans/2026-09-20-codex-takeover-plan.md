# Codex Takeover Plan — Jev Pokémon Showdown Agent

> Status: IMPLEMENTED — verified 2026-09-20
>
> This plan supersedes the historical 2026-09-19 implementation plan as the execution reference. The earlier plan is retained as provenance, but its completion claim and 15-test count are not authoritative.

## Objective

Make the local Windows demo genuinely reliable and understandable:

1. Jev plays real Gen 9 Random Battles through the Showdown/poke-env harness.
2. The harness owns protocol handling, legal-action construction, validation, and deterministic battle facts.
3. Jev receives a compact structured information state plus typed `choice` criteria and returns a typed choice, confidence, and probabilities.
4. The dashboard visibly distinguishes Showdown state, harness calculations, Jev output, adapter validation, submitted action, and the observed result.
5. A cloned repository can run the demo locally with the free OpenCode Jev route, without paid hosting or an additional LLM.

## Findings that drive this plan

### Verified working

- `.\.venv\Scripts\python.exe -m pytest -q` passes **44 tests**.
- The direct OpenCode System One route is reachable with `jev-1.13-free`; a live probe returned a typed choice, confidence, probabilities, token usage, and zero cost.
- The Jev client is asynchronous and sends the correct structured `state` plus `questions.action` with `type: choice`, `instructions`, and `criteria`.
- Candidate enumeration, fog-of-war team slots, scanner regression coverage, and the basic dashboard WebSocket are present.
- The local custom arena already renders the intended arcade-retro battle view and is coherent when shown directly.

### Release blockers and correctness gaps

- A fresh browser run showed the embedded official Showdown iframe at an empty guest lobby/room instead of the active battle. The existing validation document describes a prior manually logged-in run, so it is not reproducible clone-and-run behavior.
- `JevPlayer._record_turn` sends no `criteria`, exact question/instructions, raw Jev response, or submitted Showdown order in the `TURN_DECISION` event. The frontend has inspector slots for these values, so the current implementation is visibly less transparent than the agreed design.
- The deterministic damage annotation is a bounded base-power heuristic, not Gen 9 damage calculation. It must be labeled as an estimate or use poke-env's calculator when enough state is available.
- An empty candidate set currently produces `BattleOrder(None)`, which is not a defensible legal fallback.
- `BattleOrchestrator._on_battle_event` sets an `asyncio.Event` directly from poke-env's background loop/thread. That cross-thread event mutation is unsafe and can cause matchmaking waits to hang.
- The dashboard currently presents predicted damage/KO text under `RESULT` before Showdown has produced the result. Prediction and observed outcome must be separated.
- The header cost badge is not updated from live telemetry.
- README and validation docs contain stale claims, including the historical 15-test result and the assertion that the current iframe flow is reproducible.

## Architecture decision

### Recommended MVP: local renderer is the primary battle view

Use the existing custom arcade battle renderer as the authoritative dashboard arena. It is driven by the same battle snapshot and telemetry used by the agent, so it can reliably show active Pokémon, HP, status, revealed opponent information, fog-of-war Poké Balls, history, and Jev's action flow.

Remove the official Showdown iframe/proxy from the default path for this MVP. It adds a large amount of network/cache/frame-routing complexity, currently requires a manually persisted login state to be useful, and is not necessary to demonstrate the Jev decision boundary. Keep the official client as a documented future enhancement only if it can later be made deterministic without adding setup burden.

This preserves the visual goal while reducing the demo's failure surface:

```text
Showdown WebSocket
        ↓
poke-env battle state
        ↓
local arcade battle view + Jev Input cards
        ↓
Jev typed decision
        ↓
validator → Showdown order
        ↓
observed result + history
```

### Alternatives considered

- **Keep and repair the iframe:** visually authentic, but requires login/session synchronization and upstream-client transforms; it is the most fragile option for a public clone-and-run demo.
- **Hybrid toggle:** local renderer plus optional official iframe. This is feasible later, but adds viewer controls and two rendering paths before the core demo is reliable.
- **Recommended:** local renderer only for the MVP, with an optional future issue/branch for official-client embedding.

## Implementation tasks

### 1. Make the Jev contract and telemetry truthful

- - [x] Add a typed request/telemetry representation for the exact Jev request: model, state, question type, instructions, criteria, and redacted headers metadata.
- - [x] Preserve the exact structured Jev response fields already returned by the provider: choice, confidence, probabilities, usage, cost, model, and error status.
- - [x] Extend `TURN_DECISION` with `criteria`, `question`, `jev_response`, and the exact adapter-level submitted order/message where available. Never include authorization tokens or passwords.
- - [x] Keep raw JSON behind the technical inspector while rendering the same information as visual cards and probability bars.
- - [x] Add tests that assert the event contract and secret redaction.

### 2. Correct the legal-action and fallback boundary

- - [x] Ensure every normal choice maps to an order from the current legal candidate set.
- - [x] Replace the invalid `BattleOrder(None)` emergency path with a legal order from `battle.valid_orders` or an explicitly handled “no request/no action available” state.
- - [x] Make candidate IDs collision-safe for duplicate species/move names and robust to missing PP/category metadata.
- - [x] Add validation tests for invalid Jev choices, empty candidates, unavailable moves, forced switches, and Tera variants.

### 3. Improve deterministic battle facts without overbuilding

- - [x] Keep the complete type-chart calculation deterministic and tested.
- - [x] Use poke-env's Gen 9 damage calculator when the active Pokémon, move, target, and required stats are available.
- - [x] Retain a clearly labeled bounded estimate only for incomplete-information cases; include `calculation_mode` and assumptions in the facts.
- - [x] Avoid pretending to know hidden opponent items, abilities, EVs, IVs, or exact sets. Unknown information remains unknown to both the dashboard and Jev.
- - [x] Add compact observable facts for priority, status, weather/terrain, hazards, stat stages, and Tera availability only where the harness can read them reliably.

### 4. Make the live battle lifecycle thread-safe

- - [x] Capture the orchestrator's owning asyncio loop and signal matchmaking events with `loop.call_soon_threadsafe` from poke-env callbacks.
- - [x] Make start, match-found, battle-end, timeout, cancellation, and cleanup transitions explicit and idempotent.
- - [x] Ensure one failed battle cannot leave the dashboard stuck in `JEV PLAYING` or prevent a later retry.
- - [x] Add lifecycle tests for callback execution from a foreign thread/loop and for cleanup after Jev timeout or Showdown disconnect.

### 5. Refine the MVP dashboard for a recording

- - [x] Make the local arcade renderer the default and remove the fragile iframe from the visible primary flow.
- - [x] Keep the existing three-column hierarchy: battle view, Jev Input, Jev Output; keep history and the technical inspector because they are useful to both audiences.
- - [x] Show the complete observable sequence without implying hidden reasoning:

  `OBSERVE → CALCULATE → OPTIONS → JEV DECIDES → VALIDATE → ACT → RESULT`

- - [x] Render criteria/action explanations in the legal-action cards.
- - [x] Label calculated damage as `CALCULATED`/`ESTIMATE` and distinguish it from `OBSERVED RESULT`.
- - [x] Update model, latency, token, cost, fallback, and validation badges from live telemetry.
- - [x] Show an obvious but compact fallback banner when Jev fails; never attribute a fallback action to Jev.
- - [x] Preserve team/fog-of-war visualization: own known six, opponent revealed species only, unrevealed opponent slots as Poké Balls.
- - [x] Verify idle, searching, mid-turn, fallback, battle-end, and retry states in the actual browser at 1280×900 and 1920×1080.

### 6. Documentation and reproducibility cleanup

- - [x] Update README setup/run instructions for the actual current flow and free OpenCode route.
- - [x] Correct the benchmark documentation so it does not claim the current public benchmark is offline or Jev-free when it is not.
- - [x] Replace stale validation claims with evidence from the repaired implementation; do not claim a full public battle unless it is reproduced in the current run.
- - [x] Add a short “known limitations” section covering free-route availability, public matchmaking variability, and incomplete-information damage assumptions.
- - [x] Add the final verification commands and expected outputs to the handoff documentation.

## Verification gates

### Backend

- - [x] `.\.venv\Scripts\python.exe -m pytest -q` passes with no new application warnings caused by this work.
- - [x] Unit coverage includes Jev payload/response parsing, telemetry transparency, legal fallback, exact/fallback damage modes, snapshot fog-of-war, and lifecycle cleanup.
- - [x] A live Jev smoke probe remains optional and is never required for the offline test suite.

### Browser

- - [x] Start the server from a clean browser context.
- - [x] Confirm the idle state is useful without a Showdown iframe login.
- - [x] Click `START JEV BATTLE` and observe status transitions, at least one Jev decision, validation, act, and result telemetry.
- - [x] Inspect the rendered input/output/history panels with Playwright screenshots and console checks.
- - [x] Trigger or simulate a Jev failure and verify the dashboard says `JEV FAILED — FALLBACK USED` and shows the fallback action.
- - [x] Confirm a battle-end or simulated completion returns the UI to a retryable state.

### Live Showdown

- - [x] Run a real public Gen 9 Random Battle only after the local flow is reliable.
- - [x] Confirm no illegal order is submitted and no dashboard credentials or Jev authorization headers appear in UI/log telemetry.
- - [x] Stop/clean up the server and client after the verification run.

## Explicit non-goals

- No Claude/GPT/Gemini integration.
- No competing custom bot implementation.
- No paid hosting, database, frontend framework, or multi-agent system.
- No fabricated model reasoning or claim that Jev exposes chain-of-thought.
- No attempt to make one public battle prove human-level strength.
- No large benchmark campaign before the single-battle MVP is reliable.
