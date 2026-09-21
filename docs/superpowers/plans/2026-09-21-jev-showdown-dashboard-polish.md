# Jev Showdown Dashboard Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the dashboard into a viewport-aware Live observatory with progressive disclosure for harness/Jev telemetry and a dedicated technical Inspect workbench.

**Architecture:** Keep the existing WebSocket state projection, official Showdown renderer, and dashboard data helpers. Replace the equal-height three-column composition with a bounded battle surface plus a scroll-contained decision rail, add collapsible secondary telemetry, and turn the existing inspection drawer into a full-viewport technical mode controlled from the header and contextual links.

**Tech Stack:** Plain HTML, CSS, browser JavaScript modules, FastAPI static serving, pytest, Playwright CLI for browser smoke checks.

**Spec:** `docs/superpowers/specs/2026-09-21-jev-showdown-dashboard-polish-design.md`

## Global Constraints

- The official Showdown renderer owns the complete battle surface.
- The dashboard may display only values present in live state, telemetry, or recorded provider responses.
- No fabricated Jev reasoning, win probability, risk score, or invented metrics.
- No duplicate Pokémon, HP, team, weather, terrain, effect, battle-log, or outcome UI.
- No manual move controls, settings, replay, recording, or multi-battle orchestration.
- Backend projection, renderer integration, fallback behavior, and redaction remain unchanged unless a focused test proves a browser-safe field is missing.
- Frontend changes stay within `src/jev_showdown/web/static/` plus focused tests and dashboard documentation.

## Review Focus

- Wide and compact desktop sizing: the battle stage must not inherit the evidence rail's content height; test the viewport-aware CSS contract and inspect 1440x900, 1280x800, and 1024x768 screenshots.
- Populated legal-action data: calculated facts and the full candidate list must stay available without forcing the primary view to become thousands of pixels tall; test disclosure markup and load the real `valid-turn.json` fixture in the browser smoke check.
- Fallback and unavailable provider fields: primary Jev UI must distinguish fallback/error/unavailable values from a real Jev response; reuse existing `fallback-turn.json`, `invalid-probability.json`, and `valid-turn.json` browser states.
- Inspect accessibility: header/context actions must open the selected record, tab buttons must expose selected state and keyboard navigation, and Escape/close must return to Live; test the DOM contract and browser interaction.
- Battle ownership: only the existing `showdown-frame`/`showdown-log` surface may render the game; assert those IDs remain unique and inspect the live renderer path after layout changes.

---

### Task 1: Establish the Live/Inspect shell and progressive-disclosure markup

**Files:**
- Modify: `src/jev_showdown/web/static/index.html:12-174`
- Create: `tests/unit/test_dashboard_frontend.py`
- Test: `tests/unit/test_web_server.py:20-36`

**Interfaces:**
- Produces the stable DOM IDs `#live-view-tab`, `#open-inspector`, `#decision-rail`, `#inspection-drawer`, `#harness-calculated-disclosure`, and `#harness-legal-disclosure` for later JavaScript/CSS tasks.
- Preserves existing IDs consumed by `render.js`, `app.js`, `inspector.js`, and `showdown-renderer.js`, including `#showdown-frame`, `#showdown-log`, `#harness-observed-facts`, `#harness-calculated-facts`, `#legal-actions`, `#probability-chart`, and `#drawer-content`.

- [ ] **Step 1: Write the failing frontend contract tests**

Add `tests/unit/test_dashboard_frontend.py` with real file assertions:

```python
from pathlib import Path


ROOT = Path(__file__).parents[2]
STATIC = ROOT / "src" / "jev_showdown" / "web" / "static"


def read_static(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def test_live_shell_exposes_progressive_disclosure_regions():
    html = read_static("index.html")
    assert 'id="live-view-tab"' in html
    assert 'id="open-inspector"' in html
    assert 'id="decision-rail"' in html
    assert 'id="inspection-drawer"' in html
    assert 'id="harness-calculated-disclosure"' in html
    assert 'id="harness-legal-disclosure"' in html


def test_official_battle_surface_remains_unique():
    html = read_static("index.html")
    assert html.count('id="showdown-frame"') == 1
    assert html.count('id="showdown-log"') == 1
    assert 'id="showdown-arena"' in html


def test_inspection_tabs_remain_semantic_controls():
    html = read_static("index.html")
    assert 'role="tablist"' in html
    assert 'role="tabpanel"' in html
    assert 'data-inspect-tab="raw-event"' in html
```

- [ ] **Step 2: Run the tests and verify they fail for missing shell markup**

Run:

```powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest tests/unit/test_dashboard_frontend.py -q
```

Expected: FAIL because the current HTML has no `#decision-rail`, no Live view tab, and no disclosure IDs.

- [ ] **Step 3: Add the two-mode shell markup**

In `index.html`:

1. Add a semantic view switcher inside `.topbar-status` before the start button:

```html
<div class="view-switcher" role="tablist" aria-label="Dashboard view">
  <button id="live-view-tab" class="view-tab is-active" type="button"
          role="tab" aria-selected="true" aria-controls="live-view">LIVE</button>
  <button id="open-inspector" class="view-tab" type="button"
          role="tab" aria-selected="false" aria-controls="inspection-drawer">INSPECT</button>
</div>
```

Remove the old standalone `#open-inspector` button so there is only one control with that ID.

2. Give the existing `<main>` the `id="live-view"`, `role="tabpanel"`, and `aria-labelledby="live-view-tab"` attributes.

3. Wrap the existing harness and Jev as a single right rail, in this order, while retaining their IDs and all renderer-facing children:

```html
<div class="decision-rail" id="decision-rail">
  <!-- existing #jev-panel -->
  <!-- existing #system-harness -->
</div>
```

4. Replace the always-expanded calculated-facts and legal-action sections with native disclosures that retain their content targets:

```html
<details class="evidence-disclosure" id="harness-calculated-disclosure">
  <summary><span>CALCULATED FACTS</span><span class="source-chip source-harness">HARNESS</span></summary>
  <div id="harness-calculated-facts" class="calculation-stack"><div class="empty-row">No calculations yet</div></div>
</details>
<details class="evidence-disclosure" id="harness-legal-disclosure">
  <summary><span>LEGAL ACTION SET</span><span class="count-badge" id="legal-count">--</span></summary>
  <div id="legal-actions" class="legal-actions"><div class="empty-row">No legal candidates yet</div></div>
</details>
```

5. Replace the response-metadata section with a disclosure while retaining the existing target:

```html
<details class="evidence-disclosure" id="jev-metadata-disclosure">
  <summary><span>RESPONSE METADATA</span><span class="source-chip source-jev">RECORDED</span></summary>
  <div id="jev-metadata" class="fact-grid"><div class="empty-row">No response metadata yet</div></div>
</details>
```

6. Keep `#reliability-tiles` visible as the three compact counters; its existing `DETAILS` control continues to open the Run metrics tab. Keep `#inspection-drawer`, its tablist, `#drawer-content`, and close button in the document so `inspector.js` can be upgraded without losing existing evidence views. Add `aria-labelledby="inspection-title"` and preserve the existing `aria-hidden` initial state.

- [ ] **Step 4: Run the focused tests and the existing HTTP contract**

Run:

```powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest tests/unit/test_dashboard_frontend.py tests/unit/test_web_server.py::test_http_index -q
```

Expected: PASS, with the official renderer IDs still unique and the HTTP response still containing the dashboard shell.

- [ ] **Step 5: Commit the shell boundary**

```powershell
git add tests/unit/test_dashboard_frontend.py src/jev_showdown/web/static/index.html
git commit -m "feat: add live inspect dashboard shell"
```

### Task 2: Render a compact Live decision rail without losing evidence

**Files:**
- Modify: `src/jev_showdown/web/static/dashboard/render.js:33-146,227-248`
- Modify: `src/jev_showdown/web/static/dashboard/app.js:1-150`
- Modify: `tests/unit/test_dashboard_frontend.py`

**Interfaces:**
- `renderDashboard(clientState, selected)` continues to be the entry point called by `app.js`.
- `openInspector(tab)` and `closeInspector()` remain the public dashboard actions exposed through `window.JevShowdownDashboard`.
- New internal behavior: `setDashboardMode("live" | "inspect")` updates `#app-shell[data-view-mode]`, `#live-view-tab`, and `#open-inspector` without touching the WebSocket protocol.
- `installInspector({ getState, getSelected, setMode })` receives the existing state accessors plus a mode callback.

- [ ] **Step 1: Add failing markup/behavior contract assertions**

Append to `tests/unit/test_dashboard_frontend.py`:

```python
def test_live_view_contains_only_compact_harness_targets():
    html = read_static("index.html")
    assert 'id="harness-observed-facts"' in html
    assert 'id="harness-calculated-disclosure"' in html
    assert 'id="harness-legal-disclosure"' in html
    assert 'id="jev-metadata"' in html
    assert 'data-inspect-tab="jev-input"' in html


def test_dashboard_mode_controls_are_wired():
    app = read_static(Path("dashboard") / "app.js")
    inspector = read_static(Path("dashboard") / "inspector.js")
    assert "setDashboardMode" in app
    assert "data-view-mode" in app
    assert "setMode" in inspector
    assert "aria-selected" in inspector
```

Update `read_static` to accept `str | Path` by joining `STATIC / name` after coercing `Path(name)`.

- [ ] **Step 2: Run the focused test and verify the mode/render contract fails**

Run:

```powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest tests/unit/test_dashboard_frontend.py -q
```

Expected: FAIL because the current renderer prints all observed facts and the current app has no `setDashboardMode` or mode callback.

- [ ] **Step 3: Render compact harness facts and keep deep evidence behind disclosures**

Change `renderObserved(turn)` so the Live rail renders only these source-backed rows:

```javascript
const actions = turn?.harness?.legal_actions || [];
const rows = [
  factRow("Request", request.request_type || "Unknown"),
  factRow("Self active", activePokemon(snapshot, "self")),
  factRow("Opponent active", activePokemon(snapshot, "opponent")),
  factRow("Field", snapshot.weather || "No weather observed"),
  factRow("Legal actions", actions.length ? `${actions.length} available` : "Unavailable"),
  factRow("Unknown markers", turn?.harness?.unknowns?.length ?? 0),
];
$("#harness-observed-facts").innerHTML = rows.join("");
```

Keep `renderCalculations`, `renderLegalActions`, `renderHandoff`, `renderJev`, and `renderReliability` data-backed. Do not replace missing provider values with estimates. Preserve the selected/fallback marker in `renderLegalActions` using text (`Selected`, `Fallback`, or the existing check/warning marker) in addition to CSS color.

Wrap response metadata and run reliability in a `<details id="jev-metadata-disclosure">` section from Task 1's DOM edit, and keep probability bars visible when a valid map is returned. Render `Not returned by Jev` or `Probability map rejected` exactly as the current data state requires.

- [ ] **Step 4: Add mode state and route all inspector entry points through it**

In `app.js`, add:

```javascript
function setDashboardMode(mode) {
  const next = mode === "inspect" ? "inspect" : "live";
  const shell = query("#app-shell");
  shell.dataset.viewMode = next;
  query("#live-view-tab").setAttribute("aria-selected", String(next === "live"));
  query("#open-inspector").setAttribute("aria-selected", String(next === "inspect"));
  query("#open-inspector").setAttribute("aria-expanded", String(next === "inspect"));
  query("#inspection-drawer").setAttribute("aria-hidden", String(next !== "inspect"));
  query("#drawer-scrim").classList.toggle("is-visible", next === "inspect");
}
```

Refactor `openInspector(tab)` to call `setDashboardMode("inspect")`, dispatch the existing `jev:inspect` event, and preserve the selected decision. Refactor `closeInspector()` to call `setDashboardMode("live")` and return focus to `#live-view-tab`. Bind `#live-view-tab` to `closeInspector`, retain Escape behavior, and pass `setMode: setDashboardMode` into `installInspector`.

- [ ] **Step 5: Update inspector tab activation to preserve full evidence mode**

In `inspector.js`, keep the current tab markup and content functions. Update `setTab(tab)` so it sets both `aria-selected` and `aria-controls`/`tabIndex` for the active button. Add a stable panel ID:

```javascript
content.id = "inspection-panel";
content.setAttribute("aria-labelledby", activeTabButton?.id || "");
```

When a contextual `[data-inspect-tab]` control is clicked, call the supplied `setMode("inspect")` before rendering the requested tab. Keep the existing arrow/Home/End keyboard behavior and ensure it works after the mode switch.

- [ ] **Step 6: Run focused tests and a state-level regression suite**

Run:

```powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest tests/unit/test_dashboard_frontend.py tests/unit/test_dashboard_state.py tests/integration/test_dashboard_live.py -q
```

Expected: PASS. The state projection tests must remain unchanged because this task changes only how the existing snapshot is summarized.

- [ ] **Step 7: Commit the Live rail behavior**

```powershell
git add tests/unit/test_dashboard_frontend.py src/jev_showdown/web/static/dashboard/app.js src/jev_showdown/web/static/dashboard/render.js src/jev_showdown/web/static/dashboard/inspector.js src/jev_showdown/web/static/index.html
git commit -m "feat: add compact dashboard evidence mode"
```

### Task 3: Fit the layout to desktop and add restrained event motion

**Files:**
- Modify: `src/jev_showdown/web/static/style.css:1-260`
- Modify: `tests/unit/test_dashboard_frontend.py`

**Interfaces:**
- CSS targets the IDs/classes created by Tasks 1 and 2: `#decision-rail`, `#live-view`, `#inspection-drawer`, `.evidence-disclosure`, `.view-switcher`, and `.view-tab`.
- JavaScript event classes remain `.event-pulse`, `.event-fallback`, and the existing stage status attributes.

- [ ] **Step 1: Add failing viewport/style contract tests**

Append to `tests/unit/test_dashboard_frontend.py`:

```python
def test_dashboard_css_is_viewport_aware_and_responsive():
    css = read_static("style.css")
    assert "100dvh" in css
    assert "aspect-ratio" in css
    assert "#decision-rail" in css
    assert ".evidence-disclosure" in css
    assert "@media (max-width: 899px)" in css


def test_dashboard_css_contains_reduced_motion_equivalent():
    css = read_static("style.css")
    assert "prefers-reduced-motion: reduce" in css
    assert "animation-duration" in css
```

- [ ] **Step 2: Run the tests and verify the current CSS fails the viewport contract**

Run:

```powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest tests/unit/test_dashboard_frontend.py -q
```

Expected: FAIL because the current CSS uses a three-column `primary-grid`, lacks `100dvh`, and has no compact-desktop breakpoint at 899px.

- [ ] **Step 3: Replace the equal-height primary grid with a bounded two-column live region**

Change the core layout rules to the following shape:

```css
.dashboard-main {
  width: min(100%, 1920px);
  margin: 12px auto 0;
  display: grid;
  gap: 12px;
}

.primary-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.75fr) minmax(320px, .95fr);
  gap: 12px;
  align-items: stretch;
  min-height: 0;
  height: clamp(500px, calc(100dvh - 250px), 700px);
}

.decision-rail {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
}

.battle-stage {
  min-height: 0;
  aspect-ratio: 16 / 10;
}

.showdown-canvas,
.showdown-frame {
  width: min(100%, 920px);
  min-height: 0;
  height: 100%;
}

.evidence-panel {
  min-height: 0;
}

.panel-scroll {
  min-height: 0;
  overflow: auto;
}
```

Ensure the battle panel does not receive `grid-row: span` or a height derived from the rail's content. Use `min-height: 0` on nested grid children so long harness data scrolls inside its card.

- [ ] **Step 4: Style the progressive-disclosure rail and view switcher**

Add visible summaries for native `<details>` without introducing a new widget library:

```css
.evidence-disclosure {
  border-bottom: 1px solid var(--line-soft);
}

.evidence-disclosure > summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 44px;
  padding: 10px 12px;
  cursor: pointer;
  list-style: none;
  font: 800 .67rem var(--display);
  letter-spacing: .11em;
}

.evidence-disclosure > summary::-webkit-details-marker {
  display: none;
}

.evidence-disclosure > summary::before {
  content: "+";
  display: inline-grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border: 1px solid var(--line-soft);
  color: var(--ochre-dark);
  font-family: var(--mono);
}

.evidence-disclosure[open] > summary::before {
  content: "–";
}

.view-switcher {
  display: inline-flex;
  gap: 3px;
  padding: 3px;
  border: 1px solid #77776b;
}

.view-tab {
  min-height: 28px;
  padding: 0 8px;
  border: 0;
  background: transparent;
  color: var(--cream);
  font-size: .62rem;
  font-weight: 900;
  letter-spacing: .08em;
  cursor: pointer;
}

.view-tab[aria-selected="true"] {
  background: var(--ochre);
  color: #2a2110;
}
```

Retain the existing origin colors and result-state colors, but increase the visual hierarchy of the selected decision and reduce border repetition in secondary rows. Do not introduce decorative charts or new fabricated metrics.

- [ ] **Step 5: Turn the existing drawer into the full Inspect workbench**

Replace the current narrow drawer geometry with a mode surface:

```css
.inspection-drawer {
  position: fixed;
  z-index: 20;
  inset: 0;
  display: grid;
  grid-template-rows: auto auto auto 1fr;
  background: var(--charcoal);
  transform: translateX(102%);
  transition: transform .22s ease;
}

.app-shell[data-view-mode="inspect"] .inspection-drawer {
  transform: translateX(0);
}

.app-shell[data-view-mode="inspect"] #live-view {
  visibility: hidden;
}

.drawer-content {
  min-height: 0;
  overflow: auto;
}
```

Keep the drawer scrim available for visual separation, but the full workbench must be the accessible active surface when Inspect is selected. The Live tab must remain the clear route back.

- [ ] **Step 6: Add compact and narrow breakpoints plus event motion**

Use explicit breakpoints:

```css
@media (max-width: 1279px) {
  .topbar { gap: 10px; }
  .format-lockup { display: none; }
  .primary-grid { grid-template-columns: minmax(0, 1.35fr) minmax(300px, .9fr); }
}

@media (max-width: 899px) {
  .primary-grid,
  .decision-rail { height: auto; grid-template-columns: 1fr; grid-template-rows: none; }
  .primary-grid { display: grid; }
  .decision-rail { display: grid; }
  .battle-stage { aspect-ratio: 4 / 3; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .001ms !important;
    scroll-behavior: auto !important;
  }
}
```

Keep `.event-pulse`, `.event-fallback`, `.lifecycle-stage[data-status="active"]`, and history entrance motion restrained and state-driven. Add a short `.history-card.is-new` animation only when `renderHistory` detects a new record signature; do not continuously animate the whole dashboard.

- [ ] **Step 7: Run CSS contract and complete Python tests**

Run:

```powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest -q
```

Expected: all existing and new tests pass. Any pre-existing warnings should be reported by name rather than hidden.

- [ ] **Step 8: Commit the responsive visual system**

```powershell
git add tests/unit/test_dashboard_frontend.py src/jev_showdown/web/static/style.css
git commit -m "feat: fit dashboard to desktop viewports"
```

### Task 4: Browser verification, accessibility polish, and documentation handoff

**Files:**
- Modify: `src/jev_showdown/web/static/dashboard/app.js` if browser smoke checks expose focus/mode regressions.
- Modify: `src/jev_showdown/web/static/dashboard/inspector.js` if browser smoke checks expose tab/selection regressions.
- Modify: `docs/design/dashboard-ui-ux-design.md` only where it contradicts the implemented two-column Live rail and Inspect workbench.
- Test artifacts: `test-results/` only; do not commit generated screenshots or temporary fixture scripts.

**Interfaces:**
- Uses the real FastAPI static server at `http://localhost:8000`.
- Uses the recorded dashboard fixture `tests/fixtures/dashboard/valid-turn.json` only for local browser inspection; production code continues to receive live WebSocket state.
- Uses existing `playwright` CLI for screenshots and accessibility/browser interaction checks without adding a frontend dependency.

- [ ] **Step 1: Start the local dashboard server**

Run in a dedicated terminal session:

```powershell
uv run python -m jev_showdown.main serve --port 8000
```

Confirm the server responds before browser checks:

```powershell
Invoke-WebRequest http://localhost:8000/ -UseBasicParsing | Select-Object StatusCode
```

Expected: `200`.

- [ ] **Step 2: Capture representative Live-mode screenshots**

Run:

```powershell
playwright screenshot --viewport-size="1440,900" --wait-for-timeout=1500 http://localhost:8000 test-results/dashboard-polished-1440.png
playwright screenshot --viewport-size="1280,800" --wait-for-timeout=1500 http://localhost:8000 test-results/dashboard-polished-1280.png
playwright screenshot --viewport-size="1024,768" --wait-for-timeout=1500 http://localhost:8000 test-results/dashboard-polished-1024.png
```

Inspect each screenshot as a human viewer. The primary viewport must show a bounded battle stage, Jev summary, validation/submission state, and no right-rail-induced battle whitespace. The 1024px view must not place Jev below an unbounded harness column.

- [ ] **Step 3: Exercise Inspect mode and keyboard behavior**

Use Playwright browser interaction against the running page:

```javascript
const live = page.locator('#live-view-tab');
const inspect = page.locator('#open-inspector');
await inspect.click();
await expect(page.locator('#app-shell')).toHaveAttribute('data-view-mode', 'inspect');
await expect(inspect).toHaveAttribute('aria-selected', 'true');
await page.locator('.drawer-tab').first().press('ArrowRight');
await page.keyboard.press('Escape');
await expect(page.locator('#app-shell')).toHaveAttribute('data-view-mode', 'live');
await expect(live).toHaveAttribute('aria-selected', 'true');
```

If the MCP browser is available, use its page snapshot and screenshot tools for this check. If it remains locked, use the installed Playwright CLI/browser and record that limitation in the handoff.

- [ ] **Step 4: Exercise a populated real-data rendering path**

Use a temporary, untracked browser harness that builds a `DashboardProjector` snapshot from `tests/fixtures/dashboard/valid-turn.json` and injects only the resulting `DASHBOARD_STATE` envelope into a browser WebSocket stub. Verify visually and through text that:

- `Dracometeor (Terastallize)` appears as the returned action;
- `Returned confidence 94%` appears;
- the probability map renders only the returned values;
- legal action count and unknown markers are present in the Harness summary;
- calculated facts and the full candidate list are behind their disclosure/Inspect path;
- no prose rationale or invented win metric appears.

Delete the temporary harness and generated screenshots after inspection with explicit file paths.

- [ ] **Step 5: Exercise fallback, invalid-probability, and completion states**

Repeat the browser state injection using `fallback-turn.json`, `invalid-probability.json`, and `battle-reset.json`. Confirm fallback is labeled as fallback, rejected probability maps say they were rejected, unavailable fields remain unavailable, and completed battle state remains attributable to Showdown.

- [ ] **Step 6: Run final verification**

Run:

```powershell
$env:PYTHONPATH='.'; uv run --with pytest --with pytest-asyncio pytest -q
git diff --check
git status --short --branch
```

Expected: the full suite passes, `git diff --check` produces no output, and only intended dashboard/spec/plan changes remain. Stop the local server after browser verification.

- [ ] **Step 7: Commit any focused verification fixes and documentation alignment**

```powershell
git add src/jev_showdown/web/static/dashboard/app.js src/jev_showdown/web/static/dashboard/inspector.js docs/design/dashboard-ui-ux-design.md
git commit -m "docs: align dashboard UX notes with live workbench"
```

Do not stage `test-results/`, generated screenshots, temporary harness files, unrelated artifacts, or backend telemetry changes.
