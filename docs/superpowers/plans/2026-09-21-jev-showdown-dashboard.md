# Jev Showdown Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the public Jev Showdown dashboard around the real Showdown battle renderer, exposing truthful Harness, Jev, Adapter, and observed-result evidence in a polished Showdown Classic + Pixel Touch interface.

**Architecture:** Keep the official Showdown renderer as the only battle surface. Add a server-side dashboard projection over the existing telemetry/event stream, expose an initial snapshot plus live updates to the browser, and render the projection with focused vanilla HTML/CSS/ES modules. Use progressive disclosure: an approachable default view and a redacted structured inspection drawer for technical viewers.

**Tech Stack:** Existing Python web server and telemetry stack; official Showdown renderer assets; vanilla HTML, CSS, and ES-module JavaScript; CSS/SVG charts; existing `pytest`/`pytest-asyncio` setup; Playwright browser verification required by the product contract.

**Spec:** `docs/design/dashboard-ui-ux-design.md` and `docs/design/dashboard-product-contract.md`

## Global Constraints

- The official Showdown renderer owns the battle surface. Do not redraw or duplicate Pokémon, HP, teams, weather, terrain, messages, logs, or outcome UI.
- The dashboard observes one real autonomous battle; it is not a second battle client or a manual-play interface.
- Render live values from the application path. Omit unavailable values or label them explicitly; never fill gaps with guesses.
- Keep Showdown, Harness, Jev, and Adapter provenance visible whenever a viewer could confuse the source.
- Never manufacture Jev chain-of-thought, prose rationale, win probability, risk score, damage/KO result, confidence, cost, usage, or unsupported output.
- Render returned confidence and probabilities only when Jev returned them and validation passed. Rejected maps remain rejected evidence.
- Keep deterministic Harness annotations labeled as calculations, estimates, ranges, or unknowns, with assumptions visible.
- Never show an action as legal before validation, an order as submitted before Adapter submission, or a result as observed before Showdown reports it.
- Preserve separate battle tag, Showdown `rqid`, request `state_version`, Jev `call_id`, and event fingerprint identifiers.
- Reset decision history on a new battle and keep it inspectable after completion until the next battle begins.
- Redact secrets before data reaches the browser or technical drawer.
- Keep one active battle. Do not add manual move/order controls, replay editing, settings, or multi-battle orchestration.
- Use warm gray, cream, charcoal, ochre, muted orchid, green, amber, and coral. Blue/cyan may appear only for real Showdown or Pokémon-type data.
- Use restrained pixel styling, readable typography, hard-edged borders, shallow shadows, and reduced-motion equivalents; no blue SaaS gradient, neon cyberpunk glow, or heavy CRT effects.
- Target 1440×900 first, support 1280×800, and implement the 1024×768 narrow-landscape behavior in the design.
- Do not use the discarded `dashboard-ui-ux-mockup.png` as a visual or implementation reference. Do not add generated battle artwork or duplicate Pokémon assets.
- Preserve unrelated existing worktree changes, including the user's documentation changes and `docs/design/pokemon_showdown_live.png`.

## Review Focus

- Provider failure, timeout, invalid probability, and fallback records must remain visibly degraded and must never look like successful Jev output; pin this in projection and browser-state tests.
- A new battle must clear prior history and selection while retaining the correct `battle_tag`; pin this in projector and integration tests.
- Unknown, unavailable, inferred, and calculated values must retain source labels and must not become fake certainty; pin this in Harness and inspector tests.
- Missing raw protocol frames must be shown as missing, not implied by parsed request/order JSON; pin this in inspector tests.
- The page must remain readable at 1024×768 with keyboard access, live-region announcements, and reduced-motion behavior; pin this in browser verification.

---

## Browser data contract

The browser receives one versioned, redacted projection. Internal event types
may remain unchanged, but the browser contract is stable:

~~~text
DashboardEnvelope
  schema_version: 1
  kind: snapshot | event
  emitted_at
  run: status, format, model, endpoint_metadata, timestamps,
       evaluation_status, integrity
  battle: battle_tag, battle_id, state, winner, won, total_turns,
          replay availability
  renderer: state, connection_label, last_observed_at
  current_turn: TurnProjection | null
  history: TurnProjection[]
  metrics: battles_completed, jev_calls, valid_choices, fallbacks,
           illegal_actions, stale_responses, provider_errors,
           provider_503_errors, request_timeouts,
           protocol_validation_errors, timer_failures,
           latency_p50_ms, latency_p95_ms, latency_p99_ms
  inspection: selected_battle_tag, selected_turn, selected_call_id | null

TurnProjection
  battle_tag, turn, lifecycle_state
  showdown: request, observed_result, protocol_evidence
  harness: snapshot, request_metadata, calculated_facts,
           legal_actions, handoff_summary
  jev: request_summary, response_summary, probability_status
  adapter: validation, submitted_order, fallback
  timing: response_latency_ms, wrapper_latency_ms, decision_latency_ms
~~~

The projection must not flatten unlike fields into one invented metric.
Response, wrapper, and decision/validation latency remain separate. Candidate
legality remains separate from Adapter validation. Error-record token zeros and
empty maps are not successful zero-valued Jev output.

The verified artifact at
`artifacts/foul-play-evaluation-post-history-fix-10s-2026-09-21` supplies
test expectations only: 77 Jev calls, 84 event records, candidate counts from
1–13, 57 valid choices, 20 fallbacks, 19 provider errors, one protocol
validation error, zero illegal actions, and recorded P50/P95/P99 latency. The
live UI must consume the current event stream and must not hard-code these
values.

## File map

- Create `src/jev_showdown/web/dashboard_state.py`: projection, provenance, metrics, history isolation, and redaction.
- Create `src/jev_showdown/web/dashboard_stream.py`: in-process snapshot/event fan-out.
- Modify `src/jev_showdown/web/server.py`: shell, snapshot/stream/start routes, and telemetry connection.
- Create `src/jev_showdown/web/static/index.html`: semantic shell and renderer host.
- Create `src/jev_showdown/web/static/style.css`: visual system, layout, responsive behavior, and reduced motion.
- Create `src/jev_showdown/web/static/dashboard/app.js`: browser entry point and transport.
- Create `src/jev_showdown/web/static/dashboard/state.js`: envelope validation and client selection state.
- Create `src/jev_showdown/web/static/dashboard/render.js`: semantic Harness/Jev/Adapter/history rendering.
- Create `src/jev_showdown/web/static/dashboard/charts.js`: accessible SVG/CSS evidence charts.
- Create `src/jev_showdown/web/static/dashboard/inspector.js`: technical drawer and raw/structured views.
- Create `tests/fixtures/dashboard/{valid-turn,fallback-turn,invalid-probability,battle-reset}.json`.
- Create `tests/unit/test_dashboard_state.py`.
- Create `tests/unit/test_dashboard_stream.py`.
- Modify `tests/unit/test_web_server.py`.
- Create `tests/integration/test_dashboard_live.py`.
- Browser verification uses the configured Playwright workflow; no new runtime dependency or second browser-test framework is introduced.

Do not modify files under
`src/jev_showdown/web/static/showdown/` unless an integration test identifies
a concrete renderer defect. Reuse the existing `showdown-renderer.js` contract.

---

### Task 1: Establish the live seam and sanitized fixtures

**Files:**
- Read: `src/jev_showdown/web/server.py`, `src/jev_showdown/agent.py`
- Read: `src/jev_showdown/telemetry/events.py`, `frames.py`, `recording.py`, `serialization.py`
- Read: `src/jev_showdown/web/static/showdown-renderer.js`
- Read: `tests/unit/test_web_server.py`, `test_snapshot_and_telemetry.py`, `test_telemetry_recording.py`, `test_telemetry_serialization.py`
- Create: `tests/fixtures/dashboard/*.json`
- Create: `tests/unit/test_dashboard_state.py`

**Interfaces:**
- Consumes existing event, snapshot, request/response, validation, submitted-order, and battle-end records.
- Produces the locked mapping to `DashboardEnvelope`/`TurnProjection` and sanitized artifact-derived fixtures.

- [ ] **Step 1: Trace the current live path without changing code.** Identify the in-process decision-event boundary, renderer host contract, server framework, and existing route/test conventions. Preserve the current recorder and battle semantics.
- [ ] **Step 2: Create four small fixtures from the verified artifact:** valid response with probabilities/confidence; provider error with first-legal fallback; rejected probability with the exact validation error; and a two-battle sequence. Remove credentials, authorization material, unrelated logs, and unused fields. Mark them test-only.
- [ ] **Step 3: Write failing projector tests.** Instantiate `DashboardProjector`, call `apply_event(record)`, inspect `snapshot()`, and assert source fields, candidate count, valid choice, submitted `/choose` order, fallback reason, rejected probability state, explicit unknowns, and history reset on `BATTLE_START`.
- [ ] **Step 4: Run the focused test and confirm the expected missing-module failure.**

~~~powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest tests/unit/test_dashboard_state.py -q
~~~

- [ ] **Step 5: Commit only fixtures and tests.**

~~~powershell
git add tests/fixtures/dashboard tests/unit/test_dashboard_state.py
git commit -m "test: define dashboard projection fixtures and contract"
~~~

---

### Task 2: Implement the truthful dashboard projection

**Files:**
- Create: `src/jev_showdown/web/dashboard_state.py`
- Test: `tests/unit/test_dashboard_state.py`
- Read: `src/jev_showdown/battle/snapshot.py`, `facts.py`, `candidates.py`, `validator.py`
- Read: `src/jev_showdown/decision/protocol.py`

**Interfaces:**
- `DashboardProjector.apply_event(event: Mapping[str, Any]) -> None`
- `DashboardProjector.snapshot() -> dict[str, Any]`
- `DashboardProjector.select_decision(battle_tag: str, turn: int, call_id: int | None = None) -> dict[str, Any] | None`
- `redact_dashboard_value(value: Any) -> Any`

- [ ] **Step 1: Add event classification and JSON-safe redaction.** Handle `EVALUATION_SETUP`, `BATTLE_START`, `TURN_DECISION`, and `BATTLE_END`; preserve structured subobjects for inspection while generating compact summaries.
- [ ] **Step 2: Map Harness evidence.** Project `snapshot`, `request`, `legal_actions`, `criteria`, beliefs, hypotheses, history, opponent responses, and glossary. Preserve `observed`/`inferred`/`unknown`, move-vs-switch facts, heuristic-relative estimates, and unknown damage/KO values.
- [ ] **Step 3: Map Jev and Adapter evidence.** Project request, typed question, criteria, choice, confidence, probabilities, model, usage, cost, latency, error, validation, fallback, and submitted order under their source labels. Classify probability maps as valid, not returned, or rejected.
- [ ] **Step 4: Aggregate only recorded metrics.** Keep provider/503/timeout/protocol errors, illegal actions, stale responses, timer failures, fallback counts, latency percentiles, audit completeness, and credential-scan status distinct. Do not reinterpret error zeros.
- [ ] **Step 5: Enforce event ordering and battle isolation.** Clear history on new battle, use `battle_tag` plus turn/call IDs for selection, and prevent late prior-battle events from overwriting active state.
- [ ] **Step 6: Run focused tests.**

~~~powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest tests/unit/test_dashboard_state.py -q
~~~

Expected: PASS for valid, fallback, timeout, invalid-probability, unknown,
missing-raw-frame, cross-battle, and redaction cases.

- [ ] **Step 7: Commit the projection.**

~~~powershell
git add src/jev_showdown/web/dashboard_state.py tests/unit/test_dashboard_state.py
git commit -m "feat: add truthful dashboard state projection"
~~~

---

### Task 3: Add live snapshot and event delivery

**Files:**
- Create: `src/jev_showdown/web/dashboard_stream.py`
- Modify: `src/jev_showdown/web/server.py`
- Create: `tests/unit/test_dashboard_stream.py`
- Modify: `tests/unit/test_web_server.py`

**Interfaces:**
- `DashboardEventStream.publish(event: Mapping[str, Any]) -> None`
- `DashboardEventStream.snapshot() -> dict[str, Any]`
- `DashboardEventStream.subscribe() -> AsyncIterator[dict[str, Any]]`
- `GET /api/dashboard/state`
- `GET /api/dashboard/stream`
- `POST /api/dashboard/start`

- [ ] **Step 1: Write failing tests.** Verify a subscriber receives a redacted initial snapshot, events arrive in order, disconnects are removed, and the snapshot route matches the stream's first message. Reject manual move/order payloads at the start route.
- [ ] **Step 2: Implement a bounded async fan-out.** A slow browser must not block the battle or Jev loop. Publish only redacted envelopes; retain the existing recorder/logging path.
- [ ] **Step 3: Connect the stream at the Task 1 telemetry boundary.** Do not scrape log files or read artifact directories in the live route.
- [ ] **Step 4: Serve static shell and structured errors.** Preserve the current minimal fallback behavior for environments where the shell is unavailable; never return fake demo telemetry.
- [ ] **Step 5: Run focused server tests.**

~~~powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest tests/unit/test_dashboard_stream.py tests/unit/test_web_server.py -q
~~~

- [ ] **Step 6: Commit the transport.**

~~~powershell
git add src/jev_showdown/web/dashboard_stream.py src/jev_showdown/web/server.py tests/unit/test_dashboard_stream.py tests/unit/test_web_server.py
git commit -m "feat: stream live dashboard evidence"
~~~

---

### Task 4: Build the semantic shell around the official renderer

**Files:**
- Create: `src/jev_showdown/web/static/index.html`
- Create: `src/jev_showdown/web/static/style.css`
- Read: `src/jev_showdown/web/static/showdown-renderer.js`
- Test: `tests/unit/test_web_server.py`

**Interfaces:**
- Consumes static assets and `DashboardEnvelope`.
- Produces one renderer mount point plus semantic Harness, Jev, Adapter, current-turn, history, charts, inspector, and status-announcement regions.

- [ ] **Step 1: Write shell assertions.** Assert the HTML contains one official renderer host, origin labels, start control, technical inspection control, `aria-live` region, and no discarded PNG or generated battle artwork reference.
- [ ] **Step 2: Create the HTML structure.** Implement the top status bar, 55/22/23 main grid, current-turn evidence strip, horizontal history rail, and non-blocking drawer. Keep renderer-owned battle details inside the renderer host.
- [ ] **Step 3: Add truthful empty states.** Use `Waiting for battle`, `Waiting for public battle state`, `No decision yet`, `Connecting to Showdown`, and `Unavailable`; do not add sample Pokémon or fake counts.
- [ ] **Step 4: Add the first CSS pass.** Define warm-neutral variables, origin accents, panel framing, compact rows, hard-edged outlines, stepped corners, segmented bars, independent evidence scrolling, and the desktop/narrow grid.
- [ ] **Step 5: Run web-server tests.**

~~~powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest tests/unit/test_web_server.py -q
~~~

- [ ] **Step 6: Commit the shell.**

~~~powershell
git add src/jev_showdown/web/static/index.html src/jev_showdown/web/static/style.css tests/unit/test_web_server.py
git commit -m "feat: add semantic dashboard shell"
~~~

---

### Task 5: Implement browser transport, lifecycle, Harness, Jev, and history

**Files:**
- Create: `src/jev_showdown/web/static/dashboard/state.js`
- Create: `src/jev_showdown/web/static/dashboard/app.js`
- Create: `src/jev_showdown/web/static/dashboard/render.js`
- Modify: `src/jev_showdown/web/static/index.html`
- Modify: `src/jev_showdown/web/static/style.css`

**Interfaces:**
- Client functions: `applyEnvelope`, `selectDecision`, `clearSelection`, `renderDashboard`, `renderLifecycle`, `renderHistory`, `renderTechnicalSelection`.
- Consumes `/api/dashboard/state`, `/api/dashboard/stream`, and the existing renderer integration.

- [ ] **Step 1: Validate envelopes before rendering.** Check schema/version/kind and required lifecycle fields. Preserve unknown fields for inspection; show unavailable state for malformed data without logging secrets.
- [ ] **Step 2: Implement initial fetch and reconnect.** Keep the last valid renderer visible during stale/reconnecting state; do not reset to fake idle data.
- [ ] **Step 3: Render lifecycle truthfully.** Use `OBSERVING`, `CALCULATING`, `JEV EVALUATING`, `LEGAL`, `ORDER SUBMITTED`, `AWAITING SHOWDOWN`, `RESULT OBSERVED`, and truthful idle/error states only.
- [ ] **Step 4: Render Harness sections.** Show run context, request IDs, observed public state, calculations, assumptions, unknowns, legal candidates, and handoff. Use dynamic candidate counts and preserve stable IDs.
- [ ] **Step 5: Render Jev/Adapter sections.** Make the actual returned choice focal; show confidence/probabilities only when present and valid; show model/usage only when recorded; show exact `/choose` only after submission; keep fallback/error distinct.
- [ ] **Step 6: Render current-turn strip and history.** Use `OBSERVE → CALCULATE → OPTIONS → JEV DECIDES → VALIDATE → ACT → RESULT`; do not invent timings for derived stages. History includes battle tag, turn, action/fallback, confidence, latency, validation, submission, result, and error marker.
- [ ] **Step 7: Wire the autonomous start control.** Send only the supported start request, disable it while active, and never expose manual move/order input.
- [ ] **Step 8: Commit the lifecycle UI.**

~~~powershell
git add src/jev_showdown/web/static/index.html src/jev_showdown/web/static/style.css src/jev_showdown/web/static/dashboard
git commit -m "feat: render live harness and Jev evidence"
~~~

---

### Task 6: Add charts, technical inspection, and motion

**Files:**
- Create: `src/jev_showdown/web/static/dashboard/charts.js`
- Create: `src/jev_showdown/web/static/dashboard/inspector.js`
- Modify: `src/jev_showdown/web/static/dashboard/render.js`
- Modify: `src/jev_showdown/web/static/dashboard/app.js`
- Modify: `src/jev_showdown/web/static/style.css`

**Interfaces:**
- Chart functions: `renderProbabilityChart`, `renderLatencySummary`, `renderRunMetrics`, `renderCandidateMatrix`.
- Inspector tabs: Overview, Showdown request, Harness state snapshot, Calculated facts, Jev input, Jev response, Validation, Submitted order, Protocol evidence, Raw event, Run metrics.

- [ ] **Step 1: Test valid/rejected probability behavior.** Validated maps render returned candidate IDs and exact values; rejected maps render `Probability map rejected` plus the real error; no `Other legal actions` bucket is added.
- [ ] **Step 2: Implement accessible charts.** Use segmented bars, text/table alternatives, recorded response/wrapper/decision latency only, and optional candidate comparison with Legal/Included/Probability/Selected/Submitted columns.
- [ ] **Step 3: Implement token/cost/reliability visuals.** Keep provider errors, protocol errors, fallbacks, stale responses, illegal actions, and timer failures distinct. Mark error token zeros unavailable for billing interpretation. Show degraded evaluation status without implying strategic strength.
- [ ] **Step 4: Implement the technical drawer.** Use keyboard tabs, structured summaries before raw JSON, field paths, source labels, copy controls, expandable values, redaction markers, captured request/order evidence, and `Raw protocol frame not captured` when absent.
- [ ] **Step 5: Add event-backed motion.** Animate request handoff, valid probability arrival, selection, validation/submission, fallback, and history reveal. Add static reduced-motion equivalents; no fake thinking or prediction animation.
- [ ] **Step 6: Commit charts and inspection.**

~~~powershell
git add src/jev_showdown/web/static/dashboard src/jev_showdown/web/static/style.css
git commit -m "feat: add dashboard inspection and evidence charts"
~~~

---

### Task 7: Complete runtime states, accessibility, and responsive behavior

**Files:**
- Modify: `src/jev_showdown/web/static/index.html`
- Modify: `src/jev_showdown/web/static/style.css`
- Modify: `src/jev_showdown/web/static/dashboard/app.js`
- Modify: `src/jev_showdown/web/static/dashboard/render.js`
- Modify: `src/jev_showdown/web/static/dashboard/inspector.js`
- Create: `tests/integration/test_dashboard_live.py`

**Interfaces:**
- Consumes all envelope states and browser interactions.
- Produces idle, connecting, observing, calculating, requesting, valid response, validation/submission, awaiting-result, fallback/error, complete, stale/reconnecting, inspector-open, and narrow-landscape behavior.

- [ ] **Step 1: Add real event-path integration coverage.** Exercise the local application/event route, not only a mocked browser state. Assert fallback reason/submitted fallback, observed completion, and `Replay unavailable` when no replay exists.
- [ ] **Step 2: Add accessibility semantics.** Verify headings, buttons, disclosures, tabs, chart labels, icon names, focus rings, `aria-live` announcements, and text alternatives for color-only states. Return focus after closing the drawer.
- [ ] **Step 3: Finish 1024×768 behavior.** Keep battle first, make evidence independently scrollable or tabbed, keep current-turn strip visible, make history horizontally scrollable, and make inspector full-height without a second battle view.
- [ ] **Step 4: Audit copy and provenance.** Use SHOWDOWN, HARNESS, JEV OUTPUT, and ADAPTER labels. Keep unknown/unavailable explicit and remove unsupported marketing or strategy claims.
- [ ] **Step 5: Run integration tests.**

~~~powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest tests/integration/test_dashboard_live.py -q
~~~

- [ ] **Step 6: Commit runtime-state and accessibility work.**

~~~powershell
git add src/jev_showdown/web/static/index.html src/jev_showdown/web/static/style.css src/jev_showdown/web/static/dashboard tests/integration/test_dashboard_live.py
git commit -m "feat: complete dashboard states and accessibility"
~~~

---

### Task 8: Verify the real route and browser presentation

**Files:**
- Test: `tests/integration/test_dashboard_live.py`
- Read: `docs/design/dashboard-ui-ux-design.md`
- Read: `docs/design/dashboard-product-contract.md`

**Interfaces:**
- Consumes the running local Showdown/agent route, official renderer assets, and deterministic fixture states.
- Produces real-route and screenshot evidence for correctness and visual quality.

- [ ] **Step 1: Start the real local route.** Confirm the browser receives a live renderer and dashboard events from the application, not from artifact files.
- [ ] **Step 2: Verify 1440×900.** The battle is dominant; Harness shows state/calculation/legal/handoff evidence; Jev shows real output or truthful waiting/error; current turn/history remain readable; no duplicate battle or fake metrics appears.
- [ ] **Step 3: Verify 1024×768.** Confirm no overlap, clipping, or critical scroll failure; evidence remains usable; history scrolls; inspector is full-height.
- [ ] **Step 4: Exercise high-risk states.** Verify valid response, HTTP 503, timeout, invalid probability, fallback, stale/reconnecting, completion, replay unavailable, and missing raw frame. Check exact error/fallback text and no success-looking zero telemetry.
- [ ] **Step 5: Run automated checks and inspect screenshots.**

~~~powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest -q
~~~

Run the configured Playwright browser workflow and inspect screenshots for overflow,
overlap, unreadable text, incorrect source labels, duplicate battle UI,
broken official assets, contrast, and reduced-motion behavior.

- [ ] **Step 6: Record verification evidence.** Record commands, viewports, routes, results, and environmental limits in the implementation handoff before claiming completion.
- [ ] **Step 7: Commit integration coverage and verification updates.**

~~~powershell
git add tests/integration/test_dashboard_live.py
git commit -m "test: verify dashboard on live battle route"
~~~

---

## Requirement-to-task coverage

| Requirement | Owning tasks |
| --- | --- |
| Live Showdown screen | 1, 4, 8 |
| Full Harness transparency | 2, 5, 8 |
| Jev input without duplicated primary view | 2, 5, 6 |
| Jev output and decision boundary | 2, 5, 6, 7 |
| Decision history and turn flow | 2, 5, 7 |
| Technical inspection | 2, 6, 7 |
| Graphs/charts/visual metrics | 2, 6 |
| Showdown Classic + Pixel Touch | 4, 5, 6, 8 |
| Fallback/error/degraded states | 2, 3, 5, 7, 8 |
| Accessibility/reduced motion | 6, 7, 8 |
| Real-route/screenshot verification | 8 |

## Plan self-review checklist

- [ ] Every requirement in `dashboard-ui-ux-design.md` maps to one or more tasks.
- [ ] Every artifact-contract field has a source, rendering rule, or intentional omission.
- [ ] The official renderer is reused and no second battle UI is planned.
- [ ] Valid probabilities, rejected maps, fallbacks, provider errors, timeouts, and unavailable raw frames have separate states.
- [ ] The live path has no placeholder telemetry or unsupported Jev reasoning.
- [ ] History isolation, stale-event handling, redaction, responsive layout, keyboard access, and reduced motion have tests or browser checks.
- [ ] The plan preserves current worktree changes and does not reference the discarded mockup as an implementation input.
