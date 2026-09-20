# Dashboard Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Replace the deleted custom dashboard with a recording-ready, battle-first interface that shows the official Pokémon Showdown scene beside a truthful real-time view of harness extraction, deterministic calculations, Jev's typed decision, validation, order submission, and observed protocol results.

**Architecture:** Keep the Python battle agent, direct OpenCode System One Jev client, poke-env order flow, and official Showdown renderer as the system of record. Add a small structured decision-phase telemetry contract for the states that are currently invisible during \`choose_move\`, then build a vanilla HTML/CSS/JavaScript console that consumes those events and raw Showdown frames. The official renderer remains the only owner of Pokémon, arena, HUD, effects, messages, and outcomes; the custom layer renders only Jev observability data and compact adapter state.

**Tech Stack:** Python 3.10+, FastAPI/WebSocket, poke-env, httpx, pytest/pytest-asyncio, vanilla HTML/CSS/JavaScript, the existing local official Showdown renderer bundle, and Playwright/browser automation for visual and runtime validation.

**Spec:** \`docs/design/dashboard-canonical-spec.md\`, supported by \`docs/superpowers/specs/2026-09-20-dashboard-overhaul-design.md\`, \`docs/design/dashboard-redesign-guardrails.md\`, \`docs/design/showdown-battle-ui-direction.md\`, \`docs/research/phase-0-jev-opencode.md\`, and \`docs/research/phase-1-research-and-architecture.md\`.

## Global Constraints

- The official Pokémon Showdown renderer owns the complete live game window; the custom dashboard must not recreate its arena, Pokémon, trainers, sprites, HP bars, levels, types, statuses, stat changes, team indicators, fog of war, terrain, weather, hazards, battle messages, battle log, effects, or outcomes.
- The dashboard must not use an iframe or the full Showdown website; mount the existing \`JevShowdownRenderer\` adapter directly into the dashboard DOM.
- Use the actual Jev/OpenCode System One route and configured model; do not introduce a mock provider or simulated battle flow.
- Keep the public showcase on real \`gen9randombattle\` through the configured Showdown account and existing orchestrator.
- Jev Output may show only the actual typed choice, confidence, probabilities, configured model, measured latency, usage/cost when available, and explicit error/fallback attribution.
- Never manufacture chain-of-thought, natural-language reasoning, win chance, risk score, damage score, psychology, or an invented model version.
- Show harness-owned deterministic facts only when present in the current serialized snapshot/candidate records; omit unavailable facts rather than filling the UI with guesses.
- Jev decision history means the five most recent \`TURN_DECISION\` outputs, not the Showdown battle log or scanner history.
- Reset Jev decision history on \`BATTLE_START\`; preserve it through \`BATTLE_END\` until the next battle.
- Normal battle outcomes must preserve the official final scene and must not open a large modal overlay.
- Use the repository \`.venv\` interpreter for all Python tests and live validation.
- Do not add a frontend framework, Node build pipeline, manual move controls, settings screens, replay production, or built-in recording.
- Do not rewrite \`src/jev_showdown/web/static/showdown/\`; modify \`showdown-renderer.js\` only for a narrowly tested adapter integration need.
- The primary visual QA viewports are 1440x900 and 1600x900; the initial desktop viewport must not require page scrolling for the battle, console, status, and action trace.

## Review Focus

- A new decision begins while an earlier battle result is still visible: the UI must clear only the current decision state and never attribute the previous protocol event to the new order. Test in \`tests/unit/test_agent.py\` and the browser message-sequence test in Task 3.
- Jev times out, returns malformed/illegal output, or the provider fails before a response: the UI must show deterministic fallback attribution and action, never present the fallback as Jev's choice. Test in \`tests/unit/test_agent.py\` and the browser fallback fixture in Task 3.
- The official renderer loads slowly, rejects a frame, or cannot load \`window.Battle\`: the battle bay must show an explicit renderer failure while the Jev console and telemetry remain usable. Test adapter failure handling in Task 4 and browser validation in Task 6.
- A reconnect receives \`BATTLE_REPLAY\` but no fresh decision event: the official scene must replay into the direct renderer without clearing the console into a fake idle state. Test the existing frame buffer plus the browser replay path in Task 3.
- A decision has missing probabilities, cost, damage facts, or usage: the UI must omit those fields or show an explicit unavailable state rather than displaying zero as if it were measured. Test partial payload rendering in Task 3.

---

## File Map

The implementation is intentionally split into a small telemetry contract and a static presentation layer:

- Modify \`src/jev_showdown/decision/opencode_jev.py\` to centralize exact Jev request payload construction so live “Jev evaluating” telemetry and the actual HTTP request cannot drift.
- Modify \`src/jev_showdown/agent.py\` to emit structured decision phases, attach a stable local \`decision_id\`, reset per-battle decision history, and mark protocol-driven result observation without exposing hidden reasoning.
- Modify \`src/jev_showdown/main.py\` to forward decision-phase events through the existing \`ConnectionManager\`.
- Modify \`src/jev_showdown/telemetry/events.py\` only if a small reset/helper method is needed to make per-battle history ownership explicit.
- Modify \`tests/unit/test_jev_client.py\`, \`tests/unit/test_agent.py\`, \`tests/unit/test_orchestrator.py\`, and \`tests/unit/test_live_protocol_scanner.py\` for the new event contract and lifecycle guarantees.
- Create \`tests/unit/test_frontend_assets.py\` for the new static shell, required renderer nodes, script loading, and forbidden duplicate/iframe structures.
- Create \`src/jev_showdown/web/static/index.html\` as the semantic battle-first shell.
- Create \`src/jev_showdown/web/static/style.css\` as the restrained retro-arcade layout and responsive treatment.
- Create \`src/jev_showdown/web/static/app.js\` as the browser state machine, WebSocket router, renderer bridge, Jev console renderer, history renderer, and technical-inspection drawer.
- Inspect and test \`src/jev_showdown/web/static/showdown-renderer.js\`; modify it only if the tests demonstrate a direct-mount, replay, resize, or final-scene integration defect.
- Create \`docs/validation/2026-09-20-dashboard-rewrite-validation.md\` after implementation with exact test commands, browser evidence, screenshot paths, and real-battle evidence.

## Interfaces

### Existing backend messages consumed by the browser

The frontend must continue to handle these messages:

~~~json
{"type":"STATUS_UPDATE","status":"SEARCHING FOR OPPONENT","busy":true,"error":false}
{"type":"BATTLE_START","battle_tag":"battle-gen9randombattle-1","battle_format":"gen9randombattle"}
{"type":"TURN_DECISION","turn":1,"decision_id":"battle-gen9randombattle-1:1:1","snapshot":{},"criteria":{},"jev":{},"validation":{},"submitted_order":{},"recent_history":[]}
{"type":"BATTLE_FRAME","battle_tag":"battle-gen9randombattle-1","lines":["|turn|1"]}
{"type":"BATTLE_END","battle_tag":"battle-gen9randombattle-1","won":true,"total_turns":8}
{"type":"BATTLE_REPLAY","battle_tag":"battle-gen9randombattle-1","frames":[["|init|battle"],["|turn|1"]]}
~~~

### New decision-phase message

Add one browser-facing message with a stable shape:

~~~json
{
  "type": "DECISION_PHASE",
  "decision_id": "battle-gen9randombattle-1:1:1",
  "battle_tag": "battle-gen9randombattle-1",
  "battle_format": "gen9randombattle",
  "turn": 1,
  "phase": "JEV_EVALUATING",
  "snapshot": {},
  "request_payload": {}
}
~~~

Allowed phases and payload fields are:

- \`EXTRACTING\`: phase identity and correlation fields only.
- \`CALCULATING\`: phase identity, \`snapshot\`, and \`legal_action_count\`.
- \`JEV_EVALUATING\`: phase identity, \`snapshot\`, \`criteria\`, \`question\`, \`request_payload\`, and \`model\`.
- \`LEGAL\`: phase identity, \`validation\`, \`is_fallback\`, and \`fallback_reason\`.
- \`ORDER_SUBMITTED\`: phase identity, \`submitted_order\`, and \`is_fallback\`.
- \`AWAITING_SHOWDOWN\`: phase identity and \`submitted_order\`.
- \`RESULT_OBSERVED\`: phase identity and \`observed_commands\`; this is emitted only after a real battle protocol frame contains an action/effect/outcome command or after battle end.

The \`request_payload\` is the same JSON object passed to Jev, excluding HTTP headers. Credentials must never appear in it. The browser must not infer a Jev response from a phase event; the response is authoritative only in \`TURN_DECISION.jev\` and \`TURN_DECISION.jev_response\`.

### Shared Python request builder

Define and use:

~~~python
def build_request_payload(
    model: str,
    state: dict[str, Any],
    criteria: dict[str, str],
    instructions: str = DEFAULT_DECISION_INSTRUCTIONS,
) -> dict[str, Any]: ...
~~~

\`JevSystemOneClient.evaluate_decision()\` must call this helper, and \`JevPlayer.choose_move()\` must use the same helper for \`DECISION_PHASE.JEV_EVALUATING\` telemetry.

### Browser factory used by runtime and tests

Keep the frontend testable without a framework by exposing:

~~~javascript
window.JevDashboard = {
  create: createDashboardApp,
  summarizeProtocolLines,
};
~~~

\`createDashboardApp({ root = document, renderer = window.JevShowdownRenderer, WebSocketImpl = window.WebSocket } = {})\` returns \`{ state, handleMessage, render }\`. Runtime initialization calls the factory on \`DOMContentLoaded\); browser tests can inject a fake WebSocket and renderer.

---

### Task 1: Add truthful Jev decision-phase telemetry

**Files:**
- Modify: \`src/jev_showdown/decision/opencode_jev.py\`
- Modify: \`src/jev_showdown/agent.py\`
- Modify: \`src/jev_showdown/main.py\`
- Modify: \`src/jev_showdown/telemetry/events.py\` if needed for an explicit \`reset()\` helper
- Test: \`tests/unit/test_jev_client.py\`
- Test: \`tests/unit/test_agent.py\`
- Test: \`tests/unit/test_orchestrator.py\`
- Test: \`tests/unit/test_live_protocol_scanner.py\`

**Interfaces:**
- Consumes: existing \`JevDecisionResponse\`, \`CandidateAction\`, \`BattleSnapshotSerializer\`, \`resolve_order()\`, and raw filtered battle frames.
- Produces: \`build_request_payload()\`, \`DECISION_PHASE\` events, \`decision_id\` on every \`TURN_DECISION\`, and per-battle history reset behavior for the frontend.

- [ ] **Step 1: Write the failing request-builder and telemetry tests**

Add tests that assert:

~~~python
def test_build_request_payload_matches_http_payload():
    payload = build_request_payload(
        "jev-1.13-free",
        {"state_schema": 1, "turn": 4},
        {"move_earthquake": "Use Earthquake."},
    )
    assert payload == {
        "model": "jev-1.13-free",
        "state": {"state_schema": 1, "turn": 4},
        "questions": {
            "action": {
                "type": "choice",
                "instructions": DEFAULT_DECISION_INSTRUCTIONS,
                "criteria": {"move_earthquake": "Use Earthquake."},
            }
        },
    }
~~~

Add a \`JevPlayer\` test with a phase callback that calls \`choose_move()\` once and asserts the phase order is:

~~~python
["EXTRACTING", "CALCULATING", "JEV_EVALUATING", "LEGAL", "ORDER_SUBMITTED", "AWAITING_SHOWDOWN"]
~~~

Assert that the evaluating event contains the exact request payload, the legal event contains the fallback/validation fields, and the order event contains the exact \`BattleOrder.message\` returned by the adapter. Assert that \`TURN_DECISION.decision_id\` equals the phase events' \`decision_id\` and that credentials from a redacted response never appear in any event.

Add a test that feeds a real-looking \`|move|\`/\`|-damage|\` frame after \`AWAITING_SHOWDOWN\` and asserts exactly one \`RESULT_OBSERVED\` event with the observed protocol command names. Add a second frame with only non-result metadata and assert it does not emit a duplicate result event.

Add a per-battle reset test: seed \`history_tracker\` with one event, invoke the battle-start path, and assert the next \`TURN_DECISION.recent_history\` starts empty while the current battle's decisions accumulate normally.

Extend the orchestrator test to pass a \`DECISION_PHASE\` event through \`_on_decision_phase()\` and assert the manager receives the same JSON-safe dict.

- [ ] **Step 2: Run the focused tests and verify they fail for the missing contract**

Run:

~~~powershell
.venv\\Scripts\\python.exe -m pytest tests/unit/test_jev_client.py tests/unit/test_agent.py tests/unit/test_orchestrator.py tests/unit/test_live_protocol_scanner.py -q
~~~

Expected: failures for the missing request builder, missing phase callback/events, missing \`decision_id\`, and missing reset/result-observation behavior.

- [ ] **Step 3: Implement the shared request builder**

Move the currently inline payload construction in \`JevSystemOneClient.evaluate_decision()\` into \`build_request_payload()\` with the exact signature above. Keep authorization headers private to the HTTP call. Make \`evaluate_decision()\` pass the returned object unchanged to \`httpx.AsyncClient.post(json=payload, ...)\` and retain it in \`JevDecisionResponse.request_payload\` on success and every error path.

- [ ] **Step 4: Implement decision-phase emission in \`JevPlayer\`**

Add the optional constructor callback:

~~~python
on_decision_phase: Callable[[dict[str, Any]], Any] | None = None
~~~

Generate a monotonically increasing local sequence per player and format each ID as \`<battle_tag>:<turn>:<sequence>\`. Emit \`EXTRACTING\` before candidate construction, \`CALCULATING\` after the snapshot and candidate facts exist, and \`JEV_EVALUATING\` immediately before the async Jev call using \`build_request_payload()\`.

After \`resolve_order()\` emits \`LEGAL\`; after obtaining \`validated.order.message\` emits \`ORDER_SUBMITTED\`; immediately before returning the order emits \`AWAITING_SHOWDOWN\`. Emit \`TURN_DECISION\` with the same \`decision_id\` and the existing full snapshot/request/response/validation fields. On provider failure or invalid choice, preserve the existing deterministic fallback and include \`is_fallback\` and \`fallback_reason\` in the phase events.

Track the pending decision ID by battle tag. In \`_handle_battle_message()\`, inspect only the normalized battle lines for action/effect/outcome commands (\`move\`, \`switch\`, \`drag\`, \`-damage\`, \`-heal\`, \`-status\`, \`-stat\`, \`faint\`, \`-terastallize\`, \`win\`, \`tie\`, or \`cant\`). Emit one \`RESULT_OBSERVED\` for the pending decision, include only command names in \`observed_commands\`, and clear the pending ID. Do not copy protocol message text into the custom console.

Reset \`TurnHistoryTracker\` and pending decision state at battle creation, while preserving the existing raw frame replay behavior.

- [ ] **Step 5: Run the focused tests and confirm the event contract passes**

Run the same focused pytest command from Step 2. Expected: all focused tests pass, including provider error, illegal choice, result-frame, and per-battle reset cases.

- [ ] **Step 6: Commit the telemetry contract**

~~~powershell
git add src/jev_showdown/decision/opencode_jev.py src/jev_showdown/agent.py src/jev_showdown/main.py src/jev_showdown/telemetry/events.py tests/unit/test_jev_client.py tests/unit/test_agent.py tests/unit/test_orchestrator.py tests/unit/test_live_protocol_scanner.py
git commit -m "feat: expose truthful decision phase telemetry"
~~~

### Task 2: Create the semantic battle-first HTML shell

**Files:**
- Create: \`src/jev_showdown/web/static/index.html\`
- Create: \`tests/unit/test_frontend_assets.py\`

**Interfaces:**
- Consumes: \`JevShowdownRenderer.mount(frame, log, status)\`, \`JevShowdownRenderer.reset()\`, \`JevShowdownRenderer.feed()\`, \`JevShowdownRenderer.end()\`, and the IDs used by \`app.js\`.
- Produces: one stable DOM contract with a dominant official battle bay, one Jev console rail, a compact truth strip, and a hidden technical inspector.

- [ ] **Step 1: Write failing static asset contract tests**

Create tests that load \`index.html\` and assert the presence of these exact IDs/classes:

~~~python
required = [
    'id="start-btn"', 'id="showdown-arena"', 'id="showdown-frame"',
    'id="showdown-log"', 'id="showdown-status"', 'id="jev-input"',
    'id="jev-decision"', 'id="jev-history"', 'id="truth-strip"',
    'id="technical-inspect"', 'id="inspect-drawer"',
]
for marker in required:
    assert marker in html
~~~

Assert that the page loads \`showdown-renderer.js\` before \`app.js\`, contains no \`<iframe\`, no full Showdown website URL, no old custom LIVE BATTLE/team-panel selectors, and no duplicate HP, WEATHER, TERRAIN, BATTLE LOG, or POKÉMON HISTORY dashboard sections outside the official scene. Assert that the start control is a button and the inspector is hidden by default with an accessible label.

- [ ] **Step 2: Run the frontend contract tests and verify the expected failure**

Run:

~~~powershell
.venv\\Scripts\\python.exe -m pytest tests/unit/test_frontend_assets.py -q
~~~

Expected: failure because the three custom dashboard files are intentionally absent.

- [ ] **Step 3: Create the new semantic shell**

Build a minimal HTML document with:

~~~html
<header class="topbar">
  <div class="brand">JEV / SHOWDOWN</div>
  <div id="turn-readout"></div>
  <div id="backend-status"></div>
  <div id="showdown-connection"></div>
  <div id="jev-status"></div>
  <button id="start-btn" type="button">START JEV BATTLE</button>
</header>
<main class="battle-layout">
  <section id="showdown-arena" class="battle-bay" aria-label="Official Showdown battle scene">
    <div class="showdown-stage"><div id="showdown-frame"></div><div id="showdown-log"></div></div>
    <div id="showdown-status" class="scene-status" aria-live="polite"></div>
    <div id="renderer-fallback" hidden></div>
  </section>
  <aside class="decision-rail" aria-label="Jev decision console">
    <section id="jev-input"></section>
    <section id="jev-decision"></section>
    <section id="jev-history"></section>
    <button id="technical-inspect" type="button">TECHNICAL INSPECT</button>
  </aside>
</main>
<section id="truth-strip" aria-label="Adapter status"></section>
<aside id="inspect-drawer" hidden aria-label="Technical inspection"></aside>
~~~

Keep the actual content empty or short-state-only so JavaScript owns live data. Load the existing official renderer adapter and new app script with \`defer\`. Do not add custom Pokémon images, team rows, HP bars, battle messages, battle log copies, or explanatory marketing paragraphs.

- [ ] **Step 4: Run the static contract tests and commit the shell**

Run:

~~~powershell
.venv\\Scripts\\python.exe -m pytest tests/unit/test_frontend_assets.py -q
~~~

Expected: PASS for the semantic DOM and forbidden-structure assertions.

~~~powershell
git add src/jev_showdown/web/static/index.html tests/unit/test_frontend_assets.py
git commit -m "feat: add battle-first dashboard shell"
~~~

### Task 3: Implement the browser event state machine and Jev console

**Files:**
- Create: \`src/jev_showdown/web/static/app.js\`
- Modify: \`tests/unit/test_frontend_assets.py\` with JavaScript contract checks if useful
- Add browser fixture coverage during Task 6 using the exported \`window.JevDashboard\` factory

**Interfaces:**
- Consumes: all existing WebSocket messages plus the \`DECISION_PHASE\` contract from Task 1 and the DOM IDs from Task 2.
- Produces: \`createDashboardApp({ root, renderer, WebSocketImpl })\`, \`handleMessage(message)\`, \`render()\`, \`state\`, and \`summarizeProtocolLines(lines)\` exposed through \`window.JevDashboard\`.

- [ ] **Step 1: Write the browser contract cases before implementation**

Define browser assertions for these exact transitions:

1. \`BATTLE_START\` clears Jev history, calls \`renderer.reset(battle_tag)\`, and does not alter the official scene DOM directly.
2. \`DECISION_PHASE.JEV_EVALUATING\` shows a loading state only in \`#jev-decision\`, preserves the current input snapshot, and marks the trace as pending.
3. \`TURN_DECISION\` renders only actual \`jev\` fields, appends one history row, and displays fallback attribution when \`is_fallback\` is true.
4. \`ORDER_SUBMITTED\` shows the exact submitted order in the compact adapter trace; \`AWAITING_SHOWDOWN\` remains pending until a result frame.
5. A frame containing \`|move|\`, \`|-damage|\`, \`|faint|\`, \`|win|\`, or \`|tie|\` changes only the trace state to \`RESULT OBSERVED\`; it does not copy the protocol text into a custom result card.
6. \`BATTLE_END\` calls \`renderer.end()\` and preserves history and the final scene without opening a modal.
7. Missing \`probabilities\`, \`cost\`, usage, or deterministic facts produce omitted rows, not fabricated zero values.
8. \`BATTLE_REPLAY\` resets and feeds all frames in order, even when no new \`TURN_DECISION\` is present.

Use a fake renderer with spies and a fake WebSocket implementation so these cases can run without a live server. Keep the browser-facing test fixture independent of the provider and Showdown network.

- [ ] **Step 2: Implement the state shape and message routing**

Initialize \`state\` with explicit origins and no invented values:

~~~javascript
{
  socket: "closed",
  battleTag: null,
  battleEnded: false,
  status: { text: "READY", busy: false, error: false },
  renderer: { mounted: false, failed: false },
  current: { decisionId: null, turn: null, phase: "IDLE", input: null, decision: null, validation: null, order: null },
  history: [],
  recentFrames: [],
  inspectorOpen: false,
  inspectorSelection: null,
}
~~~

Route \`STATUS_UPDATE\` to header/start-control state, \`BATTLE_START\` to a new-battle reset, \`DECISION_PHASE\` to phase/input/validation/order state, \`TURN_DECISION\` to the authoritative decision and Jev history, \`BATTLE_FRAME\` to \`JevShowdownRenderer.feed(lines)\` plus result detection, \`BATTLE_REPLAY\` to reset/feed replay, and \`BATTLE_END\` to final-scene preservation. Ignore unknown message types without throwing a browser console error.

- [ ] **Step 3: Implement the Jev Input view**

Render only data from \`current.input\`/\`TURN_DECISION.snapshot\`/\`criteria\`:

- turn number and text-only active matchup names;
- legal action count;
- a compact list of the first four legal action labels, sorted by actual response probability only when probabilities exist;
- deterministic facts from candidate \`facts\`, including type multiplier, \`estimated_damage_range\`, \`estimated_ko\`, priority, speed, or switch cost when present;
- a short \`HARNESS-SERIALIZED STATE\` source marker and question instructions when available.

Do not display HP bars, Pokémon images, teams, weather/terrain cards, battle messages, or the raw battle log. Escape all values with \`textContent\` or DOM node creation.

- [ ] **Step 4: Implement the Jev Decision view and history**

During \`JEV_EVALUATING\`, show \`EVALUATING\` and a restrained pulse only inside \`#jev-decision\`. After \`TURN_DECISION\`, show selected typed choice, confidence, probability rows, configured model, measured Jev latency, input/output tokens, and cost only when the corresponding values are present. When \`jev.error\` or \`is_fallback\` is present, show \`FALLBACK USED\` and the exact adapter reason/action; never label that action as Jev's selected choice.

Append exactly one history row per \`TURN_DECISION\`, using turn, action label, confidence when it is a real Jev response, \`jev.latency_ms\` when nonzero, and \`ACCEPTED\` or \`FALLBACK\`. Keep only the five newest rows in visible history. Do not consume \`recent_history\` for this view because it contains protocol-scanned battle events rather than Jev decision history.

- [ ] **Step 5: Implement the compact truth strip and technical inspector**

Render three chronological segments:

~~~text
LEGAL  ->  ORDER SUBMITTED  ->  AWAITING SHOWDOWN
~~~

Use the phase event's validation and submitted-order payloads. After an actual result frame or \`BATTLE_END\`, replace the final segment with \`RESULT OBSERVED\` without repeating message/damage/result text. The inspector button opens one drawer containing formatted snapshot, request payload/question/criteria, Jev response, validation/fallback, submitted order, selected history entry, and recent raw protocol frames. Use \`<pre>\` with \`textContent\`, not HTML interpolation, and keep the drawer independently scrollable.

- [ ] **Step 6: Implement WebSocket and renderer lifecycle handling**

Connect to \`ws://\` or \`wss://\` based on \`location.protocol\`, send exactly \`{ "action": "START_BATTLE" }\` from the start button, disable the button while the backend reports \`busy\`, and expose connection loss as \`BACKEND DISCONNECTED\`/\`RECONNECTING\` without fabricating a battle state. Mount the direct renderer once with \`showdown-frame\`, \`showdown-log\`, and \`showdown-status\`; queue frames through the adapter; catch mount/feed failures and show \`OFFICIAL SHOWDOWN RENDERER UNAVAILABLE — TELEMETRY FALLBACK ACTIVE\` while leaving the console active.

- [ ] **Step 7: Run syntax/static checks and commit the browser logic**

Run:

~~~powershell
.venv\\Scripts\\python.exe -m pytest tests/unit/test_frontend_assets.py -q
node --check src/jev_showdown/web/static/app.js
~~~

Expected: static assertions and JavaScript syntax checks pass. If Node is unavailable, run the same syntax check through the browser automation environment before committing.

~~~powershell
git add src/jev_showdown/web/static/app.js tests/unit/test_frontend_assets.py
git commit -m "feat: render live Jev observability telemetry"
~~~

### Task 4: Implement the restrained arcade layout and renderer boundary

**Files:**
- Create: \`src/jev_showdown/web/static/style.css\`
- Inspect/modify only if required: \`src/jev_showdown/web/static/showdown-renderer.js\`
- Modify: \`tests/unit/test_showdown_renderer_assets.py\` and \`tests/unit/test_frontend_assets.py\` for direct-mount/asset-boundary assertions

**Interfaces:**
- Consumes: the DOM shell from Task 2, the state classes/attributes rendered by Task 3, and the existing official renderer's fixed 640x360 scene.
- Produces: a 16:9 battle bay with a right-side console, compact trace, independently scrolling inspector, and no iframe/full-client path.

- [ ] **Step 1: Add failing layout and renderer-boundary assertions**

Assert in static tests that CSS contains the exact layout invariants:

~~~python
assert "aspect-ratio: 16 / 9" in css
assert "grid-template-columns" in css
assert "overflow-x: hidden" in css
assert "@media" in css
~~~

Assert that \`index.html\` has no iframe and that \`showdown-renderer.js\` still references the local official bundle, \`window.Battle\`, \`BASE_WIDTH = 640\`, \`BASE_HEIGHT = 360\`, and \`JevShowdownRenderer\`. Do not assert or add a custom Pokémon scene.

- [ ] **Step 2: Implement the desktop composition**

Use a single main grid with the battle bay taking roughly 70% of available width and the decision rail roughly 30%. Give the battle stage an exact 16:9 host ratio; let \`showdown-renderer.js\` scale its fixed 640x360 frame with \`transform\` and set the host height so the official scene is not cropped. Position the official log/status nodes inside the bay rather than in a separate block underneath. Keep the truth strip compact below the main grid.

- [ ] **Step 3: Implement visual hierarchy without generic card clutter**

Use deep indigo/navy surfaces, a small number of purposeful borders, readable monospace/pixel-adjacent system fonts, restrained amber/blue/green/red state accents, and clear spacing. Make the current Jev decision the rail focal point; keep input, history, and inspection subordinate. Do not add slogans, duplicated \`LIVE BATTLE\` labels, a large pipeline diagram, decorative neon telemetry, generated Pokémon art, or paragraphs that explain visible UI.

- [ ] **Step 4: Implement responsive and failure styles**

At widths below the desktop composition, collapse the decision rail below the battle bay without shrinking the official scene into an unreadable thumbnail. Allow the inspector drawer to occupy the full width. Add explicit styles for \`.renderer-unavailable\`, \`[data-phase="JEV_EVALUATING"]\`, fallback/error states, disabled start, and battle-ended/final-scene states. Keep page-level horizontal overflow hidden and allow only the inspector/history internals to scroll.

- [ ] **Step 5: Make the smallest adapter change only if browser evidence requires it**

Keep the current adapter's direct \`Battle\` mount, local asset loading, protocol feed queue, resize observer, \`reset()\`, and \`end()\` behavior. If browser validation reveals a real integration defect, change only the failing boundary: preserve the \`640x360\` dimensions, keep frames queued before bundle load, keep \`end()\` from destroying the final scene, and surface a rejected frame through \`setUnavailable()\` without throwing out of the WebSocket handler. Do not edit files below \`src/jev_showdown/web/static/showdown/\`.

- [ ] **Step 6: Run asset/layout checks and commit the visual boundary**

Run:

~~~powershell
.venv\\Scripts\\python.exe -m pytest tests/unit/test_showdown_renderer_assets.py tests/unit/test_frontend_assets.py -q
node --check src/jev_showdown/web/static/app.js
~~~

Expected: PASS with no iframe/asset-boundary regressions.

~~~powershell
git add src/jev_showdown/web/static/style.css src/jev_showdown/web/static/showdown-renderer.js tests/unit/test_showdown_renderer_assets.py tests/unit/test_frontend_assets.py
git commit -m "feat: style official battle bay and Jev console"
~~~

### Task 5: Run the complete automated suite and contract review

**Files:**
- Inspect: all modified source/tests from Tasks 1–4
- Modify only if a test exposes a contract defect: the owning source/test file

**Interfaces:**
- Consumes: the complete backend event contract and static dashboard implementation.
- Produces: a passing automated baseline before live browser and battle validation.

- [ ] **Step 1: Run the full relevant pytest suite**

Run:

~~~powershell
.venv\\Scripts\\python.exe -m pytest -q
~~~

Expected: all existing and new tests pass. Record the exact count and warnings; check the source of every new application warning.

- [ ] **Step 2: Review event ordering and secret boundaries**

Inspect a captured unit-test event sequence and verify that:

~~~text
EXTRACTING -> CALCULATING -> JEV_EVALUATING -> LEGAL -> TURN_DECISION -> ORDER_SUBMITTED -> AWAITING_SHOWDOWN -> RESULT_OBSERVED
~~~

is only used when each phase actually occurred. Confirm that \`Authorization\`, passwords, tokens, and API keys do not appear in \`DECISION_PHASE\`, \`TURN_DECISION\`, inspector JSON, or test fixtures.

- [ ] **Step 3: Compare the implementation against the canonical spec line by line**

Check every required custom surface, excluded duplicate, loading/fallback rule, history rule, viewport rule, and renderer ownership rule. Remove any UI element that is not backed by a real event or deterministic fact. Add a focused test before fixing any discovered contract gap.

- [ ] **Step 4: Commit the automated baseline**

~~~powershell
git add .
git commit -m "test: verify dashboard rewrite contracts"
~~~

### Task 6: Validate the real browser and live Jev battle

**Files:**
- Create: \`docs/validation/2026-09-20-dashboard-rewrite-validation.md\`
- Inspect: \`.env\` by variable names only, \`src/jev_showdown/main.py\`, \`src/jev_showdown/web/server.py\`, browser console/network/WebSocket logs, and screenshots

**Interfaces:**
- Consumes: the local server started by \`.venv\\Scripts\\python.exe -m jev_showdown.main serve --port 8000\`, actual configured Jev/OpenCode responses, actual public Showdown frames, and the browser state machine.
- Produces: evidence that the screen is visually coherent, technically truthful, and suitable for recording.

- [ ] **Step 1: Start the dashboard with the project interpreter**

Run:

~~~powershell
.venv\\Scripts\\python.exe -m jev_showdown.main serve --port 8000
~~~

Open \`http://127.0.0.1:8000/\` with browser automation at 1440x900 and 1600x900. Confirm the idle view has one clear start control, a dominant official battle bay area, an empty/ready Jev console, no horizontal overflow, and no duplicate Pokémon UI.

- [ ] **Step 2: Exercise the startup and WebSocket flow**

Click \`START JEV BATTLE\` once. Capture the visible sequence from \`READY\` through connection/authentication/search/match initialization and \`JEV PLAYING\`. Verify the button is not duplicated, does not allow concurrent starts, and shows errors from the backend without replacing the scene with a modal.

- [ ] **Step 3: Inspect a real Jev decision**

During one actual decision, verify the browser shows loading only in the Jev decision area, then shows the actual selected typed action, confidence, probability distribution, model identifier, measured latency, usage/cost when returned, legal-action count, serialized matchup, and available deterministic facts. Open \`TECHNICAL INSPECT\` and verify the exact request, response, validation, submitted order, and recent raw frames are present without credentials.

- [ ] **Step 4: Observe the official scene and temporal truth**

Verify sprites, arena, official HP/status/team UI, messages, effects, switches, faint, and final outcome come from the official renderer. Confirm the custom trace remains \`AWAITING SHOWDOWN\` until a protocol frame arrives, then changes only to \`RESULT OBSERVED\` without duplicating the battle message or damage.

- [ ] **Step 5: Exercise fallback and renderer degradation paths**

Use a controlled test fixture or provider failure path to verify the UI says \`FALLBACK USED\`, names the adapter reason/action, and does not claim Jev selected the fallback. Temporarily make the renderer mount reject in a browser fixture and verify the telemetry fallback remains readable with explicit renderer attribution.

- [ ] **Step 6: Exercise battle end and reset**

Allow a real battle to end or use a captured protocol fixture. Confirm the official final scene remains visible, no large result modal appears, the five most recent Jev decisions remain visible, and a subsequent \`BATTLE_START\` clears the old decision history before the next turn.

- [ ] **Step 7: Record evidence and perform final human review**

Write \`docs/validation/2026-09-20-dashboard-rewrite-validation.md\` with:

- exact Python/pytest command and result;
- browser viewport sizes and screenshot paths;
- idle, startup, evaluating, accepted decision, fallback, inspector, battle-end, and reset observations;
- console, network, and WebSocket error results;
- actual Jev model/latency/usage/cost observations without secrets;
- real battle format, number of observed turns, and honest battle outcome evidence;
- any renderer or public-matchmaking limitations.

Review the screenshots as a human viewer and remove anything that duplicates Showdown, invents Jev behavior, creates avoidable blank space, or makes the technical pipeline harder to understand. Do not declare completion from a page-load check alone.

- [ ] **Step 8: Commit the validation evidence and final state**

~~~powershell
git add docs/validation/2026-09-20-dashboard-rewrite-validation.md src tests
git commit -m "docs: record dashboard rewrite validation evidence"
git status --short --branch
~~~

Expected: the working tree is clean and the validation document contains reproducible evidence for automated tests, browser inspection, and at least one real battle path.

## Self-Review

- **Spec coverage:** Tasks 1–4 cover the truthful phase contract, Jev Input, Jev Decision, decision-only history, technical inspection, official renderer ownership, 16:9 composition, fallback/error states, responsive behavior, and no-fluff copy. Tasks 5–6 cover full test and runtime acceptance evidence.
- **Placeholder scan:** Every step names the affected behavior and expected command/result; no step depends on an unspecified future decision.
- **Type consistency:** \`build_request_payload()\`, \`DECISION_PHASE\`, \`decision_id\`, \`createDashboardApp()\`, \`handleMessage()\`, \`render()\`, and \`summarizeProtocolLines()\` are defined once and reused consistently across tasks.
- **Review focus coverage:** Provider failure/illegal choice is covered in Task 1 and Task 3; renderer failure in Task 4 and Task 6; reconnect replay in Task 3 and Task 6; partial data omission in Task 3; temporal attribution and per-battle reset in Task 1, Task 3, and Task 6.
- **Historical documents:** Earlier plans and mockup-oriented documents remain historical. The canonical specification and this plan supersede conflicting duplicate-game-UI or iframe directions.

