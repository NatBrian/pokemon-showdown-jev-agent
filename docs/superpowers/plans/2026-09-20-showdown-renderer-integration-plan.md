# Official Showdown Battle Renderer Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or **superpowers:executing-plans** to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dashboard's hand-built battle-stage approximation with the official Pokémon Showdown battle renderer, fed by the real protocol stream from the running Jev match, while preserving the Jev observability panels and a transparent fallback.

**Architecture:** `poke-env` already receives the authoritative Showdown protocol. The backend will forward bounded raw battle frames over the existing dashboard WebSocket and retain a short replay for reconnects. A small browser adapter will load the audited official renderer bundle, create one `Battle` instance in a normal DOM element (never an iframe), and feed those frames to Showdown's own animation/protocol engine. The existing custom arena remains as a clearly labelled fallback only; Jev Input, Jev Output, validation, action, and observed-result panels remain custom dashboard UI around the official battle stage.

**Tech Stack:** Python 3.11, FastAPI/Starlette WebSockets, `poke-env`, pytest, static HTML/CSS/JavaScript, official Pokémon Showdown client battle renderer/data/CSS, official hosted sprite/background/FX resources.

**Spec:** `docs/design/showdown-battle-ui-direction.md`

## Global Constraints

- The live battle area must use the official Pokémon Showdown battle renderer, not a hand-built approximation of Pokémon battle effects.
- The visual target is a polished Pokémon Black/White-inspired 2D/2.5D battle presentation powered by the official Showdown renderer and surrounded by a transparent Jev observability cockpit.
- The effect layer must be driven by the same observed protocol stream; it must never invent a successful hit, damage amount, terrain, or weather state merely because Jev selected a move.
- Do not include the full Showdown website window, an iframe, chat, advertisements, matchmaking controls, a 3D engine, or a second battle engine.
- Keep the project simple: no new Node/Electron runtime and no new frontend framework; load the renderer as static browser assets from the existing FastAPI app.
- Preserve the existing real OpenCode Jev path and real Showdown Gen 9 Random Battles harness; no mock Jev or simulated battle path may become the default.
- Preserve attribution and exact upstream license notices for every vendored renderer file; document the source revision and the fact that hosted sprites/effects remain official Showdown resources.
- The visual hierarchy is battle stage first, Jev Input/Output second, and technical telemetry in the bottom VALIDATE → ACT → OBSERVED RESULT strip.

## Review Focus

- A browser reconnects after a battle has begun: it must receive enough bounded raw protocol history to render the current scene rather than showing an empty arena.
- A protocol batch contains multiple lines, a blank line, a non-battle room, or malformed text: only the correct battle lines must reach the renderer and the browser must remain usable.
- The official renderer assets fail to load or `window.Battle` cannot initialize: the user must see a clear fallback state and the existing telemetry view must still work.
- A narrow desktop viewport or a 16:9 recording viewport resizes the battle panel: the fixed-size official scene must scale without clipping the arena or overlapping Jev panels.
- A real move/switch/damage/weather/terrain/faint sequence arrives: the scene must be driven by Showdown protocol timing, while the custom panels continue to reflect Jev telemetry and observed results.

---

## File Map

Create or modify only these focused boundaries:

- Create `src/jev_showdown/telemetry/frames.py` — bounded per-battle raw-frame replay buffer with no browser concerns.
- Modify `src/jev_showdown/agent.py` — emit raw battle protocol batches after filtering them to one battle room.
- Modify `src/jev_showdown/main.py` — bridge raw frame events to the existing dashboard connection manager.
- Modify `src/jev_showdown/web/server.py` — retain and replay raw frames to dashboard clients.
- Create `src/jev_showdown/web/static/showdown/` — audited official renderer JavaScript/data/CSS subset and `NOTICE.md`.
- Create `src/jev_showdown/web/static/showdown-renderer.js` — browser-only loader/mount/feed adapter for the official `Battle` global.
- Modify `src/jev_showdown/web/static/index.html` — add the official battle stage shell and load the adapter; keep the custom arena as fallback.
- Modify `src/jev_showdown/web/static/app.js` — consume `BATTLE_FRAME`/`BATTLE_REPLAY`, drive the adapter, and surface renderer fallback status.
- Modify `src/jev_showdown/web/static/style.css` — implement the two-column battle-first recording layout and scaled renderer viewport.
- Create `tests/unit/test_battle_frames.py` — replay-buffer tests.
- Modify `tests/unit/test_agent.py`, `tests/unit/test_live_protocol_scanner.py`, `tests/unit/test_orchestrator.py`, `tests/unit/test_web_server.py` — raw-frame transport coverage.
- Modify `tests/unit/test_frontend_assets.py` — renderer shell, asset, no-iframe, and fallback contract coverage.
- Create `docs/validation/showdown-renderer-demo-checklist.md` — evidence-based browser/backend validation checklist and result record.

## Interface Contract

The backend emits these JSON messages over the existing dashboard WebSocket:

```json
{
  "type": "BATTLE_FRAME",
  "battle_tag": "battle-gen9randombattle-1",
  "lines": ["|turn|1", "|move|p1a: Pikachu|Thunderbolt|p2a: Gyarados"]
}
```

When a dashboard client connects during an active or recently completed battle, it may receive:

```json
{
  "type": "BATTLE_REPLAY",
  "battle_tag": "battle-gen9randombattle-1",
  "frames": [["|init|battle"], ["|switch|p1a: Pikachu|Pikachu, L50"], ["|turn|1"]]
}
```

`BattleFrameBuffer` must expose:

```python
class BattleFrameBuffer:
    def __init__(self, max_frames: int = 400) -> None: ...
    def start(self, battle_tag: str) -> None: ...
    def append(self, battle_tag: str, lines: list[str]) -> None: ...
    def replay(self) -> dict[str, object] | None: ...
```

`JevPlayer` accepts an optional `on_battle_frame: Callable[[dict[str, Any]], Any] | None` callback. The orchestrator publishes the resulting `BATTLE_FRAME` message through `ConnectionManager.publish`.

The browser adapter exposes:

```javascript
window.JevShowdownRenderer = {
  mount: async function (frameElement, logElement, statusElement) {},
  reset: function (battleTag) {},
  feed: function (lines) {},
  setUnavailable: function (message) {},
  destroy: function () {}
};
```

## Task 1: Raw Protocol Frames and Reconnect Replay

**Files:**
- Create: `src/jev_showdown/telemetry/frames.py`
- Modify: `src/jev_showdown/agent.py`, `src/jev_showdown/main.py`, `src/jev_showdown/web/server.py`
- Test: `tests/unit/test_battle_frames.py`, `tests/unit/test_agent.py`, `tests/unit/test_live_protocol_scanner.py`, `tests/unit/test_orchestrator.py`, `tests/unit/test_web_server.py`

**Interfaces:**
- Consumes: raw `split_messages: list[list[str]]` from `JevPlayer._handle_battle_message` and existing lifecycle callbacks.
- Produces: `BATTLE_FRAME` events and `BATTLE_REPLAY` on a new dashboard connection; existing `TURN_DECISION` and lifecycle messages remain unchanged.

- [ ] **Step 1: Write the failing tests**

Add tests that assert:

```python
def test_frame_buffer_keeps_only_latest_bounded_frames():
    buffer = BattleFrameBuffer(max_frames=2)
    buffer.start("battle-1")
    buffer.append("battle-1", ["|turn|1"])
    buffer.append("battle-1", ["|turn|2"])
    buffer.append("battle-1", ["|turn|3"])
    assert buffer.replay() == {
        "type": "BATTLE_REPLAY",
        "battle_tag": "battle-1",
        "frames": [["|turn|2"], ["|turn|3"]],
    }
```

Add an agent test that sends a battle-tagged protocol batch and asserts exactly one callback payload with the tag and filtered lines. Add an orchestrator test that publishes `BATTLE_FRAME`. Add a connection-manager test that connects a new WebSocket after `BATTLE_FRAME` publication and receives `BATTLE_REPLAY` before ordinary live messages.

- [ ] **Step 2: Run the focused tests to verify RED**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests/unit/test_battle_frames.py tests/unit/test_live_protocol_scanner.py tests/unit/test_agent.py tests/unit/test_orchestrator.py tests/unit/test_web_server.py -q
```

Expected: FAIL because `BattleFrameBuffer`, the `on_battle_frame` callback, and the replay message do not exist yet. Existing unrelated tests may pass.

- [ ] **Step 3: Implement the smallest transport path**

Implement `BattleFrameBuffer` with a bounded `deque`, reset it on `start`, ignore appends for another battle tag, and return a JSON-ready replay object. In `JevPlayer._handle_battle_message`, reuse the existing battle-room filtering and emit the raw non-empty lines once per incoming batch after the scanner receives them. In `BattleOrchestrator`, pass `self._on_battle_frame` into `JevPlayer` and publish the event. In `ConnectionManager`, remember `BATTLE_START`/`BATTLE_FRAME` messages and have `connect` send the current replay immediately after accepting the socket.

Keep replay bounded by frames rather than bytes, with the default `max_frames=400`. Do not alter action validation or Jev decision ordering.

- [ ] **Step 4: Run the focused tests to verify GREEN**

Run the same pytest command. Expected: all named raw-frame, callback, bridge, and replay tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/jev_showdown/telemetry/frames.py src/jev_showdown/agent.py src/jev_showdown/main.py src/jev_showdown/web/server.py tests/unit/test_battle_frames.py tests/unit/test_agent.py tests/unit/test_live_protocol_scanner.py tests/unit/test_orchestrator.py tests/unit/test_web_server.py
git commit -m "feat: stream raw showdown battle frames"
```

## Task 2: Vendor the Audited Official Renderer Subset

**Files:**
- Create: `src/jev_showdown/web/static/showdown/NOTICE.md`
- Create: `src/jev_showdown/web/static/showdown/js/lib/ps-polyfill.js`, `src/jev_showdown/web/static/showdown/js/lib/jquery-1.11.0.min.js`, `src/jev_showdown/web/static/showdown/js/lib/html-sanitizer-minified.js`, `src/jev_showdown/web/static/showdown/js/battle-sound.js`, `src/jev_showdown/web/static/showdown/js/battledata.js`, `src/jev_showdown/web/static/showdown/js/battle-tooltips.js`, `src/jev_showdown/web/static/showdown/js/battle.js`
- Create: `src/jev_showdown/web/static/showdown/data/pokedex-mini.js`, `pokedex-mini-bw.js`, `graphics.js`, `pokedex.js`, `moves.js`, `abilities.js`, `items.js`, and `style/battle.css`, `style/battle-log.css`
- Test: `tests/unit/test_showdown_renderer_assets.py`

**Interfaces:**
- Consumes: the exact renderer subset identified in `docs/research/github-showdown-visual-integration.md`.
- Produces: browser-loadable scripts and CSS in the existing FastAPI static directory; no Python import or Node build step.

- [ ] **Step 1: Write the failing asset-contract tests**

Create tests that require these files and no silent substitute:

```python
REQUIRED = {
    "js/lib/ps-polyfill.js", "js/lib/jquery-1.11.0.min.js",
    "js/lib/html-sanitizer-minified.js", "js/battle-sound.js",
    "js/battledata.js", "data/pokedex-mini.js", "data/pokedex-mini-bw.js",
    "data/graphics.js", "data/pokedex.js", "data/moves.js",
    "data/abilities.js", "data/items.js", "js/battle-tooltips.js",
    "js/battle.js", "style/battle.css", "style/battle-log.css", "NOTICE.md",
}

def test_official_renderer_subset_is_present():
    assert REQUIRED <= {path.relative_to(RENDERER_ROOT).as_posix() for path in RENDERER_ROOT.rglob("*") if path.is_file()}

def test_renderer_notice_identifies_source_and_licenses():
    notice = (RENDERER_ROOT / "NOTICE.md").read_text(encoding="utf-8")
    assert "pokemon-showdown-client" in notice
    assert "showdown" in notice.lower()
    assert "license" in notice.lower()
```

- [ ] **Step 2: Run the asset tests to verify RED**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests/unit/test_showdown_renderer_assets.py -q
```

Expected: FAIL because the renderer directory is not yet present.

- [ ] **Step 3: Copy and audit the minimum renderer files**

Copy the proven 17-file renderer/data/CSS subset from the audited Nidozo reference or the corresponding official client revision into the static directory using its CDN-compatible `js/lib`, `js`, `data`, and `style` paths. Preserve all upstream headers byte-for-byte. Inspect each source header and record in `NOTICE.md`:

- upstream repository URL;
- exact source commit or fetched revision;
- per-file license statements where the files differ;
- Nidozo as the integration reference only, not as a license grant;
- official Showdown CDN URLs used by the CSS/config for sprites, backgrounds, and FX.

Do not copy Nidozo application code, LLM code, React code, Electron code, or the full official client. If the renderer files use relative `fx/` or `sprites/` paths, configure the adapter to point at the official hosted resources instead of introducing a large new asset tree.

- [ ] **Step 4: Run the asset tests to verify GREEN**

Run the focused test and then verify that all copied files are readable as UTF-8 or binary as appropriate. Expected: the required subset and notice test pass.

- [ ] **Step 5: Commit**

```powershell
git add src/jev_showdown/web/static/showdown tests/unit/test_showdown_renderer_assets.py
git commit -m "feat: add audited showdown battle renderer assets"
```

## Task 3: Mount the Official Battle Scene in the Dashboard

**Files:**
- Create: `src/jev_showdown/web/static/showdown-renderer.js`
- Modify: `src/jev_showdown/web/static/index.html`, `src/jev_showdown/web/static/app.js`, `src/jev_showdown/web/static/style.css`
- Test: `tests/unit/test_frontend_assets.py`

**Interfaces:**
- Consumes: `BATTLE_FRAME`/`BATTLE_REPLAY` from Task 1 and static assets from Task 2.
- Produces: `window.JevShowdownRenderer.mount/reset/feed/setUnavailable/destroy`; an official battle stage in `#showdown-arena` and an existing custom fallback in `#arena-fallback`.

- [ ] **Step 1: Write the failing frontend contract tests**

Extend the frontend asset tests to assert:

```python
def test_dashboard_has_official_showdown_stage_and_adapter():
    html = INDEX.read_text(encoding="utf-8")
    assert 'id="showdown-arena"' in html
    assert 'id="showdown-frame"' in html
    assert 'id="showdown-log"' in html
    assert 'showdown-renderer.js' in html
    assert "<iframe" not in html.lower()

def test_adapter_loads_renderer_in_dependency_order_and_handles_replay():
    adapter = (STATIC / "showdown-renderer.js").read_text(encoding="utf-8")
    assert "window.JevShowdownRenderer" in adapter
    assert "battle.js" in adapter
    assert "BATTLE_REPLAY" not in adapter  # message routing stays in app.js
    assert "battle.add" in adapter
    assert "battle.play" in adapter
```

Add a static contract test for the battle-first grid classes and the visible `VALIDATE`, `ACT`, and `OBSERVED RESULT` labels.

- [ ] **Step 2: Run the focused frontend tests to verify RED**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests/unit/test_frontend_assets.py -q
```

Expected: FAIL because the official stage and adapter are not present.

- [ ] **Step 3: Implement the browser adapter and HTML shell**

Implement `showdown-renderer.js` as a singleton loader:

1. Set `window.Config.routes.client` to the official client base URL expected by the renderer.
2. Load the CSS once.
3. Load the scripts in dependency order: `js/lib/ps-polyfill.js`, `js/lib/jquery-1.11.0.min.js`, `js/lib/html-sanitizer-minified.js`, `js/battle-sound.js`, `js/battledata.js`, `data/pokedex-mini.js`, `data/pokedex-mini-bw.js`, `data/graphics.js`, `data/pokedex.js`, `data/moves.js`, `data/abilities.js`, `data/items.js`, `js/battle-tooltips.js`, then `js/battle.js`.
4. On `mount`, create `new window.Battle({$frame, $logFrame, id, subscription})` using the DOM nodes and call the renderer's normal lifecycle methods.
5. On `feed(lines)`, call `battle.add(line)` for each line and then `battle.play()`.
6. Use `ResizeObserver` to scale the fixed 640×360/400 Showdown scene to its shell without clipping; keep status text outside the scene for loading/unavailable errors.
7. Catch asset and constructor failures, mark the renderer unavailable, and leave the existing custom arena fallback usable.

Add to `index.html`:

```html
<section class="showdown-arena" id="showdown-arena" aria-label="Live Pokémon Showdown battle" hidden>
  <div class="showdown-stage-shell">
    <div class="showdown-stage-viewport" id="showdown-frame"></div>
    <div class="showdown-log-viewport" id="showdown-log"></div>
  </div>
  <p class="showdown-renderer-status" id="showdown-status">SHOWDOWN RENDERER LOADING…</p>
</section>
```

Keep `#arena-fallback` in the DOM but label it `TELEMETRY FALLBACK — OFFICIAL SCENE UNAVAILABLE`; the adapter toggles it only when needed.

- [ ] **Step 4: Implement routing and battle-first layout**

In `app.js`, route `BATTLE_START` to `reset`, `BATTLE_FRAME` to `feed`, and each frame in `BATTLE_REPLAY` to `feed` in order. Mount lazily on the first start/frame so an idle dashboard does not load the renderer unnecessarily. Do not derive effects from `TURN_DECISION`.

In `style.css`, use a two-column layout:

```css
.dashboard-grid {
  grid-template-columns: minmax(0, 1.6fr) minmax(360px, 0.85fr);
}
.panel-battle { grid-column: 1; grid-row: 1 / span 2; }
.panel-input { grid-column: 2; grid-row: 1; }
.panel-output { grid-column: 2; grid-row: 2; }
```

Keep the bottom decision strip full width and collapse to one column below the existing narrow viewport breakpoint. The arena should dominate a 16:9 desktop recording while the Jev Input/Output panels remain readable.

- [ ] **Step 5: Run the focused frontend tests to verify GREEN**

Run the same focused test command. Expected: all official-stage, dependency-order, no-iframe, labels, and layout contract tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src/jev_showdown/web/static/index.html src/jev_showdown/web/static/app.js src/jev_showdown/web/static/style.css src/jev_showdown/web/static/showdown-renderer.js tests/unit/test_frontend_assets.py
git commit -m "feat: render live battles with official showdown scene"
```

## Task 4: Integration Hardening and Demo Documentation

**Files:**
- Modify: `src/jev_showdown/web/static/app.js`, `src/jev_showdown/web/server.py`, `tests/unit/test_frontend_assets.py`, and any focused implementation files required by failing tests.
- Create: `docs/validation/showdown-renderer-demo-checklist.md`

**Interfaces:**
- Consumes: all previous task contracts.
- Produces: a documented, repeatable real-browser validation record for a real Jev/OpenCode/Showdown battle.

- [ ] **Step 1: Add failure-path tests before hardening**

Add tests that assert:

- an empty or malformed `lines` array is ignored rather than sent to `Battle.add`;
- a frame for another battle tag is not appended to the active replay;
- the frontend contains visible fallback copy mentioning that the official renderer is unavailable and that telemetry remains available;
- `BATTLE_END` leaves the final official scene visible and still renders the observed result.

- [ ] **Step 2: Run those tests to verify RED**

Run the focused unit/frontend test command and confirm each new failure-path test fails before its production fix.

- [ ] **Step 3: Implement the smallest hardening fixes**

Normalize lines at the backend boundary, ignore empty frame batches in the browser adapter, preserve the last completed scene until the next `BATTLE_START`, and keep the existing observed-result rendering independent of renderer availability. Ensure renderer errors are surfaced in the status copy and browser console without crashing `app.js`.

- [ ] **Step 4: Run the complete automated suite**

Run:

```powershell
.\.venv\Scripts\pytest.exe -q
```

Expected: all existing and new tests pass.

- [ ] **Step 5: Run a real backend/browser validation**

Start the local FastAPI dashboard using the repository's documented `.venv` command and use Playwright against `http://127.0.0.1:8000`. Record:

- renderer asset requests and HTTP status;
- WebSocket connection and receipt of `BATTLE_START`, `BATTLE_FRAME`, `TURN_DECISION`, and `BATTLE_END`;
- browser console errors and warnings;
- screenshot at idle, an active move/effect, and post-battle result;
- whether the official arena visibly shows both sides, HP/status UI, terrain/weather/effects when the real protocol reports them;
- Jev model name, confidence/distribution, latency, validation, action, and observed result in the surrounding panels;
- fallback behavior if the renderer asset is intentionally unavailable in a separate local check.

Do not claim a move effect was observed unless it is visible in the official renderer or supported by the received protocol log.

- [ ] **Step 6: Write the validation checklist and commit**

Create `docs/validation/showdown-renderer-demo-checklist.md` with checkbox sections for technical correctness, real-time reliability, visual quality, storytelling, transparency, and recording readiness. Include the date, local command, viewport, battle format, asset source, test command, and actual results. Commit:

```powershell
git add docs/validation/showdown-renderer-demo-checklist.md src tests
git commit -m "test: validate official showdown battle demo"
```

## Final Verification

- [ ] Run `git status --short` and confirm only intentional committed changes exist.
- [ ] Run `.\.venv\Scripts\pytest.exe -q` and record the exact count.
- [ ] Run the local dashboard and inspect the rendered page with Playwright, not only source files.
- [ ] Take a fresh screenshot and compare it to `docs/design/showdown-battle-ui-mockup-v1.png`: battle stage remains the visual focus, Jev Input/Output remain readable, and the bottom truth strip is visible.
- [ ] Verify no iframe or complete Showdown website chrome is used.
- [ ] Verify the final scene is official Showdown output driven by raw protocol, with custom fallback only on renderer failure.
- [ ] Complete a final self-review because no subagent tool is available in this session, and record any deferred minor findings in the execution ledger.
