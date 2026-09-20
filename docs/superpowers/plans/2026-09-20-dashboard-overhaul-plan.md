# Dashboard Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the accumulated widget-grid dashboard with a tightly fitted official Showdown battle bay, a compact Jev Input/Decision rail, truthful action trace, and hidden technical inspection surface.

**Architecture:** Keep the existing FastAPI/WebSocket, Jev, poke-env, and official Showdown renderer contracts. Rebuild the static dashboard shell and its presentation state machine in vanilla HTML/CSS/JavaScript. The official renderer remains the only game-state visual; the custom rail renders only harness/adapter/Jev data already present in `TURN_DECISION`, `STATUS_UPDATE`, and raw battle-frame events.

**Tech Stack:** Existing vanilla HTML, CSS, JavaScript, FastAPI static serving, official Showdown client bundle, Python pytest, Node syntax checks, Playwright MCP for visual/runtime validation.

**Spec:** `docs/superpowers/specs/2026-09-20-dashboard-overhaul-design.md`

## Global Constraints

- Preserve the existing Jev/OpenCode API, battle strategy, Showdown WebSocket flow, and fallback selection behavior.
- Use the official Showdown renderer and raw protocol for battle visuals; do not rebuild Pokémon sprites, terrain, weather, effects, HP/team HUD, or animation.
- The official battle bay must use the exact 640×360 scene composition inside a 16:9 host viewport; the adapter base height is 360, not 380.
- Do not place a separate log/status block below the battle stage; the latest message is an overlay or caption inside the battle bay.
- Do not duplicate active Pokémon, team, terrain, weather, hazard, HP, or battle-history components outside the official scene.
- Jev Output may show only actual response/adapter fields: choice, confidence, probabilities, model, latency, usage/cost when available, and fallback/error state.
- Never manufacture chain-of-thought, win chance, damage score, risk score, invented model version, or psychological explanation.
- `VALIDATE → ACT → OBSERVED RESULT` is chronological; `OBSERVED RESULT` remains pending until Showdown reports the result.
- Normal outcomes must not use a large modal overlay.
- Technical Inspection is hidden by default and is the single-click path to detailed state, request, response, validation, and protocol data.
- Primary browser QA viewport is 1440×900 or 1600×900; the first viewport must not require scrolling for the battle, rail, status, and action trace.
- Do not add a frontend framework or build pipeline. No new bitmap asset is required; use CSS for the outer arcade frame. If a non-Pokémon bitmap becomes necessary, generate it with imagegen and commit it separately.

## Review Focus

- Fast battle completion or renderer-mount races must preserve the final official scene and outcome status rather than reverting to idle or overwriting the result.
- A slow or failed official renderer must expose the existing telemetry fallback with explicit renderer attribution and must not leave a blank battle bay.
- Jev failure or invalid choice must visibly identify adapter fallback and its action without presenting fallback as Jev output.
- The compact rail must remain readable at 1440×900 and 1600×900 without duplicating the official Pokémon HUD or forcing page scrolling.
- A decision must never display a predicted or unrelated event as the current action's observed result; pending and protocol-resolved states must be distinct.

---

### Task 1: Replace the dashboard DOM with the agreed semantic shell

**Files:**
- Modify: `src/jev_showdown/web/static/index.html`
- Modify: `tests/unit/test_frontend_assets.py`

**Interfaces:**
- Consumes: existing DOM ids required by `app.js` and `showdown-renderer.js`, especially `start-btn`, `showdown-arena`, `showdown-frame`, `showdown-log`, `showdown-status`, and the WebSocket lifecycle.
- Produces: stable semantic regions for the new header status rail, `battle-bay`, `decision-rail`, `jev-input`, `jev-output`, `truth-strip`, `technical-inspect`, and inspector drawer.

- [ ] **Step 1: Write failing contract tests for the new shell**

Replace the old layout assertions in `tests/unit/test_frontend_assets.py` with assertions for the new regions and explicit removal of obsolete duplicated regions:

```python
assert 'class="battle-bay"' in html
assert 'class="decision-rail"' in html
assert 'id="jev-input"' in html
assert 'id="jev-output"' in html
assert 'id="truth-strip"' in html
assert 'id="technical-inspect"' in html
assert 'id="inspect-drawer"' in html
assert 'id="showdown-arena"' in html
assert 'id="showdown-frame"' in html
assert 'id="showdown-log"' in html
assert 'id="end-overlay"' not in html
assert 'id="history-cards"' not in html
assert 'id="self-team-slots"' not in html
assert 'id="opp-team-slots"' not in html
assert 'OBSERVABLE DATA' not in html
assert 'SAME GAME. DEEPER INSIGHT.' not in html
```

- [ ] **Step 2: Run the focused contract tests and verify the expected failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_frontend_assets.py -q
```

Expected: failure because the current HTML still contains the old three-region panel grid, history/team nodes, and end overlay.

- [ ] **Step 3: Write the minimal semantic HTML shell**

Replace the current `index.html` body with these regions while retaining the official renderer mount nodes:

```html
<header class="topbar">
  <div class="brand-mark" aria-hidden="true"></div>
  <div class="brand-copy"><h1>JEV BATTLE AGENT</h1><span>GEN 9 RANDOM BATTLES</span></div>
  <div class="system-status" aria-label="System status">
    <span id="backend-status" class="status-chip">BACKEND --</span>
    <span id="showdown-connection-status" class="status-chip">SHOWDOWN --</span>
    <span id="jev-status" class="status-chip">JEV --</span>
  </div>
  <span id="game-state" class="game-state">IDLE</span>
  <button id="start-btn" class="arcade-btn" type="button">START JEV BATTLE</button>
</header>

<main class="dashboard-main">
  <section class="battle-bay" aria-label="Official Pokémon Showdown battle">
    <div id="showdown-arena" class="showdown-arena" hidden>
      <div class="showdown-stage-canvas">
        <div id="showdown-frame" class="showdown-stage-viewport"></div>
        <div id="showdown-log" class="showdown-log-viewport"></div>
        <div id="showdown-caption" class="showdown-caption" aria-live="polite"></div>
        <div id="showdown-status" class="showdown-status">SHOWDOWN --</div>
      </div>
    </div>
    <div id="arena-fallback" class="arena-fallback" hidden>
      <strong>TELEMETRY FALLBACK</strong>
      <span id="fallback-arena-copy">OFFICIAL SHOWDOWN RENDERER UNAVAILABLE</span>
    </div>
  </section>

  <aside class="decision-rail" aria-label="Jev decision telemetry">
    <section id="jev-input" class="decision-card">
      <header><h2>JEV INPUT</h2><span>HARNESS</span></header>
      <div id="input-summary"></div>
      <div id="input-facts" class="fact-chips"></div>
      <div id="legal-actions" class="legal-actions"></div>
    </section>
    <section id="jev-output" class="decision-card">
      <header><h2>JEV DECISION</h2><span id="decision-source">--</span></header>
      <div id="jev-loader" class="jev-loader" hidden></div>
      <div id="decision-choice"></div>
      <div id="decision-confidence"></div>
      <div id="decision-probabilities" class="probabilities"></div>
      <div id="decision-meta"></div>
      <div id="fallback-banner" hidden></div>
    </section>
  </aside>
</main>

<footer id="truth-strip" class="truth-strip">
  <div id="validate-step"></div><span aria-hidden="true">→</span>
  <div id="act-step"></div><span aria-hidden="true">→</span>
  <div id="result-step"></div>
  <button id="technical-inspect" type="button">TECHNICAL INSPECT</button>
</footer>

<aside id="inspect-drawer" class="inspect-drawer" hidden aria-label="Technical inspection">
  <button id="inspect-close" type="button">CLOSE</button>
  <div id="inspect-tabs"></div>
  <pre id="inspect-content"></pre>
</aside>
```

The exact copy may use the existing project typography, but the shell must not reintroduce duplicate team, terrain, weather, history, or normal-outcome modal components.

- [ ] **Step 4: Run the focused contract tests**

Run the same pytest command. Expected: the new shell assertions pass; stale-JavaScript assertions may still fail until Task 3.

- [ ] **Step 5: Commit the semantic shell**

```powershell
git add src/jev_showdown/web/static/index.html tests/unit/test_frontend_assets.py
git commit -m "refactor: replace dashboard with battle-first shell"
```

### Task 2: Fit the official renderer into the 16:9 battle bay

**Files:**
- Modify: `src/jev_showdown/web/static/showdown-renderer.js`
- Modify: `src/jev_showdown/web/static/style.css`
- Modify: `tests/unit/test_frontend_assets.py`

**Interfaces:**
- Consumes: existing `JevShowdownRenderer.mount(frame, log, status)`, `feed(lines)`, `reset(tag)`, `end()`, and `setUnavailable(message)`.
- Produces: an exact 640×360 renderer coordinate system scaled into an aspect-ratio 16:9 host, with the log/caption visually inside the bay.

- [ ] **Step 1: Add failing sizing and ownership assertions**

Add static assertions:

```python
adapter = _read(os.path.join(static_dir, "showdown-renderer.js"))
css = _read(os.path.join(static_dir, "style.css"))
assert "const BASE_HEIGHT = 360" in adapter
assert "const BASE_HEIGHT = 380" not in adapter
assert "aspect-ratio: 16 / 9" in css
assert "showdown-stage-canvas" in css
assert "position: absolute" in css
assert "showdown-log-viewport" in css
```

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_frontend_assets.py -q
```

Expected: failure because the current adapter uses a 380px base height and the current host layout leaves the log/status block outside the stage.

- [ ] **Step 2: Implement the exact renderer sizing**

In `showdown-renderer.js`:

```javascript
const BASE_WIDTH = 640;
const BASE_HEIGHT = 360;
```

Keep the official `Battle` constructor and protocol feed unchanged. Update `resizeStage()` to size the canvas from its width while preserving 16:9, set the official frame to 640×360, and scale without cropping. Preserve the end-state race protection and renderer fallback behavior.

- [ ] **Step 3: Implement the tight battle-bay CSS**

Use the official scene as the filled visual region:

```css
.battle-bay { min-width: 0; min-height: 0; }
.showdown-arena { width: 100%; aspect-ratio: 16 / 9; overflow: hidden; }
.showdown-stage-canvas { position: relative; width: 100%; aspect-ratio: 16 / 9; overflow: hidden; }
.showdown-stage-viewport { position: absolute; inset: 0 auto auto 0; width: 640px; height: 360px; transform-origin: top left; }
.showdown-log-viewport { position: absolute; left: 12px; right: 12px; bottom: 12px; max-height: 72px; overflow: hidden; z-index: 4; }
.showdown-log-viewport .battle-log { width: 100%; height: auto; max-height: 72px; overflow: hidden; }
.showdown-caption { position: absolute; left: 12px; right: 12px; bottom: 12px; z-index: 5; pointer-events: none; }
.showdown-status { position: absolute; top: 8px; left: 12px; z-index: 6; }
```

Do not add a second block below the battle stage. Make the right decision rail stretch to the battle bay height. Keep the outer styling to thin pixel/arcade framing and avoid adding blank decorative space.

- [ ] **Step 4: Run syntax and focused tests**

```powershell
node --check src/jev_showdown/web/static/showdown-renderer.js
.venv\Scripts\python.exe -m pytest tests/unit/test_frontend_assets.py -q
```

Expected: both pass for renderer sizing and official-stage contract assertions.

- [ ] **Step 5: Commit the renderer host update**

```powershell
git add src/jev_showdown/web/static/showdown-renderer.js src/jev_showdown/web/static/style.css tests/unit/test_frontend_assets.py
git commit -m "refactor: fit showdown renderer to battle bay"
```

### Task 3: Replace the presentation state machine with Jev-only telemetry

**Files:**
- Modify: `src/jev_showdown/web/static/app.js`
- Modify: `src/jev_showdown/web/static/style.css`
- Modify: `tests/unit/test_frontend_assets.py`

**Interfaces:**
- Consumes: `STATUS_UPDATE`, `BATTLE_START`, `BATTLE_FRAME`, `BATTLE_REPLAY`, `TURN_DECISION`, and `BATTLE_END` messages already emitted by the backend.
- Produces: input summary, real Jev output, top-K legal actions/facts, status chips, truthful truth-strip states, and inspector cache.

- [ ] **Step 1: Add failing assertions for removed duplicate renderers and actual Jev fields**

Update the frontend contract tests:

```python
assert "renderActiveMons" not in js
assert "renderTeams" not in js
assert "renderHistory" not in js
assert "closeOverlay" not in js
assert "win chance" not in js.lower()
assert "risk (faint)" not in js.lower()
assert "MODEL v3.1" not in js
assert "probabilities" in js
assert "fallback_reason" in js
assert "jev-1.13-free" not in js  # model comes from the event, not a hardcoded label
```

Run the focused frontend tests and verify they fail against the current presentation code.

- [ ] **Step 2: Define the small client state used by the new view**

Keep the existing WebSocket and renderer state, and add only presentation state:

```javascript
const state = {
  ws: null,
  connected: false,
  battleActive: false,
  gamePhase: "IDLE",
  showdownBattleTag: null,
  showdownMountPromise: null,
  showdownUnavailable: false,
  inspectOpen: false,
  inspectTab: "state",
  inspect: { state: null, question: null, request: null, response: null, validation: null, frames: [] },
  currentTurn: null,
  currentDecision: null,
  awaitingObservedResult: false,
};
```

Do not add a second state store for Pokémon rendering; the official renderer owns that state.

- [ ] **Step 3: Implement truthful status mapping**

Update `handleStatusUpdate`, `handleShowdownBattleStart`, `handleShowdownFrame`, and `handleBattleEnd` to set:

```javascript
setStatusChip("backend-status", state.connected ? "BACKEND ONLINE" : "BACKEND OFFLINE");
setStatusChip("showdown-connection-status", "SHOWDOWN " + showdownState);
setStatusChip("jev-status", fallback ? "JEV FALLBACK" : "JEV " + modelOrState);
setText("game-state", phase);
```

Use `JEV PLAYING` while active, disable the start button during a battle, and preserve `SHOWDOWN BATTLE ENDED — FINAL SCENE PRESERVED` after end events. Renderer failures must switch to the explicitly labelled fallback region.

- [ ] **Step 4: Implement the Jev Input summary**

Replace the old center-panel renderer with `renderJevInput(snapshot, criteria, chosenId)`:

```javascript
const legal = Array.isArray(snapshot?.legal_actions) ? snapshot.legal_actions : [];
const selected = legal.find((action) => action.id === chosenId);
renderInputSummary({
  turn: snapshot?.turn,
  self: snapshot?.self?.active_pokemon?.species,
  opponent: snapshot?.opponent?.active_pokemon?.species,
  legalCount: legal.length,
  field: snapshot?.fields || [],
});
renderFactChips(selected?.facts || {});
renderTopKLegalActions(legal, criteria, chosenId, 4);
```

Show a selected action plus up to four useful legal alternatives, always keeping the selected action visible. Do not render duplicate sprites, HP bars, team rows, or separate terrain/weather panels.

- [ ] **Step 5: Implement actual Jev Output rendering**

Replace the old right-panel renderer with `renderJevOutput(jev, validation, chosenId, snapshot)` using only:

```javascript
setText("decision-source", jev.model || "MODEL UNAVAILABLE");
setText("decision-choice", chosenId || "AWAITING DECISION");
setText("decision-confidence", fmtPct(jev.confidence));
renderProbabilities(jev.probabilities || {}, snapshot?.legal_actions || [], chosenId);
setText("decision-meta", `${fmtLatency(jev.latency_ms)} MS · IN ${jev.input_tokens ?? "--"} · OUT ${jev.output_tokens ?? "--"}`);
```

Show fallback reason and action only when `validation.is_fallback` is true. Keep inference loading animation localized to `jev-output`.

- [ ] **Step 6: Implement the truthful action trace**

Update `renderActionTrace` so a new decision sets:

```text
VALIDATE: LEGAL ACTION
ACT: ORDER READY / SUBMITTED
OBSERVED RESULT: AWAITING SHOWDOWN
```

When a raw battle frame reports a resolved move/damage/status/faint/turn event, update only the observed-result text from that protocol event. Never use a predicted criteria string as the observed result. Preserve the last result after `BATTLE_END`.

- [ ] **Step 7: Remove obsolete presentation code and syntax-check**

Delete the old custom Pokémon cards, team renderers, duplicate field renderers, turn-history renderer, end overlay handlers, and unused sprite helpers from `app.js`. Keep only the renderer fallback path and the official Showdown adapter integration.

Run:

```powershell
node --check src/jev_showdown/web/static/app.js
.venv\Scripts\python.exe -m pytest tests/unit/test_frontend_assets.py -q
```

- [ ] **Step 8: Commit the Jev telemetry presentation**

```powershell
git add src/jev_showdown/web/static/app.js src/jev_showdown/web/static/style.css tests/unit/test_frontend_assets.py
git commit -m "refactor: simplify dashboard telemetry rail"
```

### Task 4: Add the single-click technical inspector and responsive behavior

**Files:**
- Modify: `src/jev_showdown/web/static/index.html`
- Modify: `src/jev_showdown/web/static/app.js`
- Modify: `src/jev_showdown/web/static/style.css`
- Modify: `tests/unit/test_frontend_assets.py`

**Interfaces:**
- Consumes: the cached snapshot, question/criteria, request, response, validation, and battle-frame data from Task 3.
- Produces: a hidden-by-default inspector drawer with explicit close control and independent scrolling.

- [ ] **Step 1: Add failing inspector contract assertions**

```python
assert 'id="technical-inspect"' in html
assert 'id="inspect-drawer"' in html
assert 'id="inspect-close"' in html
assert 'state' in js.lower()
assert 'question' in js.lower()
assert 'response' in js.lower()
assert 'BATTLE_FRAME' in js
```

Run the focused tests and verify the drawer behavior assertions fail before implementation.

- [ ] **Step 2: Implement drawer open/close and tabs**

Use one button and one drawer. Tabs must expose `STATE`, `JEV REQUEST`, `JEV RESPONSE`, `VALIDATION`, and `PROTOCOL`. Render JSON with `JSON.stringify(value, null, 2)` only inside the drawer. Update `state.inspect` on every `TURN_DECISION` and append bounded frame history on every `BATTLE_FRAME`.

- [ ] **Step 3: Implement responsive CSS**

At desktop, use a single viewport grid. At widths below 900px, stack the decision rail below the battle bay and keep the inspector independently scrollable. Do not allow responsive rules to reintroduce a three-column dashboard or shrink the battle scene below readable size at the primary recording viewport.

- [ ] **Step 4: Verify focused tests and JavaScript syntax**

```powershell
node --check src/jev_showdown/web/static/app.js
.venv\Scripts\python.exe -m pytest tests/unit/test_frontend_assets.py -q
```

- [ ] **Step 5: Commit inspector and responsive behavior**

```powershell
git add src/jev_showdown/web/static/index.html src/jev_showdown/web/static/app.js src/jev_showdown/web/static/style.css tests/unit/test_frontend_assets.py
git commit -m "feat: add dashboard technical inspector"
```

### Task 5: Run full verification and real browser visual QA

**Files:**
- Create: `docs/validation/2026-09-20-dashboard-overhaul-validation.md`
- Verify: `src/jev_showdown/web/static/index.html`
- Verify: `src/jev_showdown/web/static/style.css`
- Verify: `src/jev_showdown/web/static/app.js`
- Verify: `src/jev_showdown/web/static/showdown-renderer.js`

**Interfaces:**
- Consumes: the complete rebuilt dashboard and the existing local Jev/Showdown runtime.
- Produces: automated test evidence, Playwright visual evidence, and a concise readiness report.

- [ ] **Step 1: Run the complete automated suite**

```powershell
.venv\Scripts\python.exe -m pytest -q
node --check src/jev_showdown/web/static/app.js
node --check src/jev_showdown/web/static/showdown-renderer.js
```

Expected: all Python tests pass; both JavaScript syntax checks pass.

- [ ] **Step 2: Start the local dashboard using the repository venv**

```powershell
Start-Process .venv\Scripts\python.exe -ArgumentList '-m','jev_showdown.main','serve','--port','8000'
```

Open `http://127.0.0.1:8000/` in Playwright and set the browser viewport to exactly `1440×900` or `1600×900` before taking screenshots.

- [ ] **Step 3: Validate the idle view visually**

Confirm with a screenshot and visual inspection:

- no page scrolling is needed;
- the battle bay and decision rail are aligned;
- no duplicate game-state widgets, old slogans, or normal outcome overlay appear;
- the status rail clearly says backend/Showdown/Jev state;
- `START JEV BATTLE` is the only primary action while idle.

- [ ] **Step 4: Validate a synthetic decision lifecycle**

Inject or publish a representative `TURN_DECISION` using the existing event shape and verify:

- Jev Input shows active names, legal-action count, top-K actions, and real candidate facts;
- Jev Output shows the selected choice, real confidence, probabilities, model, and latency;
- the selected action is highlighted;
- the truth strip is `LEGAL ACTION → ORDER READY/SUBMITTED → AWAITING SHOWDOWN`;
- Technical Inspection opens in one click and contains the request/response/validation data.

- [ ] **Step 5: Validate a real live battle**

Click `START JEV BATTLE` and confirm:

- the official Showdown stage renders real sprites, team indicators, HP/status, arena, effects, and battle messages;
- the scene is tightly fitted to the 16:9 bay with no separate log/status block below;
- Jev inference is visibly the only meaningful wait;
- the decision rail updates from real Jev/OpenCode data;
- fallback state is explicit if triggered;
- battle end preserves the final official scene and shows the observed result in place.

- [ ] **Step 6: Check browser/runtime signals**

Use Playwright console and network inspection plus server logs. Record zero application console errors, no required static asset failures, a connected WebSocket, and a live battle lifecycle. Existing dependency deprecation warnings may be recorded separately if unchanged.

- [ ] **Step 7: Write the validation checklist and commit**

The validation document must record the viewport, test command/result, visual checks, live battle outcome, fallback/error checks, and any non-blocking caveat. Then run:

```powershell
git add docs/validation/2026-09-20-dashboard-overhaul-validation.md
git commit -m "test: validate dashboard overhaul"
```

## Final Plan Self-Review

- Spec coverage: the plan covers the three core experiences, duplication removal, exact Showdown viewport, transparency, technical inspection, status/error states, no modal outcomes, responsive behavior, imagegen boundary, and Playwright visual validation.
- Completeness scan: no unfinished-task markers or vague "handle appropriately" steps remain; each task names files, selectors, event fields, commands, and expected outcomes.
- Type/interface consistency: the plan preserves the existing renderer methods and event names and uses exact snapshot/JeV event fields from `agent.py` and `snapshot.py`.
- Review focus: all five high-risk cases are listed and assigned to frontend contract, renderer adapter, lifecycle, or browser-validation tests.
- Scope: no backend strategy rewrite, new frontend framework, or generated Pokémon asset is included.
