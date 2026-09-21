# Jev Showdown Dashboard Polish Design

Status: design approved in conversation; implementation pending.

## Goal

Make the local Jev Showdown dashboard feel like a focused live observatory: the official battle remains the visual anchor, a normal viewer can understand the current turn without reading telemetry, and a technical viewer can inspect the complete recorded decision boundary without overwhelming the primary view.

## Product constraints

- The official Showdown renderer owns the complete battle surface.
- The dashboard may display only values present in the live state, telemetry, or recorded provider response.
- Harness facts, Jev output, adapter validation, and Showdown observations remain visibly attributable.
- No fabricated chain-of-thought, prose rationale, win probability, risk score, or invented metrics.
- No duplicate Pokémon, HP, team, weather, terrain, effect, battle-log, or outcome UI.
- No manual move controls, settings screen, replay system, recording workflow, or multi-battle orchestration.
- Existing WebSocket state projection, renderer integration, fallback behavior, and redaction remain unchanged unless a concrete UI defect requires a narrow supporting change.

## Design principles

1. **Battle first.** The live renderer receives the largest stable surface and must not be stretched by the height of telemetry content.
2. **Progressive disclosure.** The default Live view communicates the current turn; detailed state and raw records live in an explicit Inspect workbench.
3. **One visual question per component.** A component exists to answer what is happening now, where the data came from, or what a technical viewer can inspect.
4. **Motion marks events.** Animation is reserved for connection, lifecycle, decision, fallback, and history changes; idle screens remain calm.
5. **Truthful density.** Compact summaries are allowed, but they must link to the underlying recorded object rather than replace it with an inference.

## Information architecture

The page has two modes selected from the header:

### Live mode

Live mode is the default and is optimized for a normal desktop viewer. It contains:

- a compact operational header with product identity, format, battle tag, connection state, current turn, and the existing start control;
- the official Showdown battle surface;
- a right decision rail with the returned Jev decision above a compact harness summary;
- a current-turn lifecycle strip;
- a compact decision-history rail.

The right rail shows only the current-turn summary by default:

- Jev selected action, only when actually returned;
- returned confidence and returned probabilities, only when present;
- validation status;
- submitted order status;
- a small set of current harness facts: request type, active Pokémon labels, field condition, legal-action count, and unknown count;
- an explicit disclosure control for the full legal action set and calculated facts.

The legal action disclosure may start open when the current turn is being evaluated, but it must be contained within the rail and must not determine the height of the battle surface. It must show the selected or fallback action using text and structure in addition to color.

### Inspect mode

Inspect mode is opened by the existing `INSPECT` control or a contextual `VIEW DETAILS` action. It uses the full available viewport as a technical workbench rather than an always-visible wall of fields.

The workbench contains:

- a sticky workbench header with the selected decision label and a close/live control;
- a horizontally scrollable, keyboard-navigable tab rail;
- one independently scrollable content pane;
- the existing structured views for overview, Showdown request, harness state, calculated facts, Jev input, Jev response, validation, submitted order, protocol evidence, raw event, and run metrics;
- copy controls for redacted JSON only.

The workbench must preserve the current selection when opened from a history card or a contextual link. Opening it without a decision continues to show the empty state and must not invent sample data.

## Responsive layout

### Wide desktop: 1280px and above

- The application shell uses the viewport width without a narrow fixed max-width that leaves unused desktop space.
- The main live region is a fixed-height, viewport-aware grid derived from `100dvh`, with a safe minimum and maximum. It must fit the battle, lifecycle strip, and history header in a normal 1440x900 viewport without forcing the battle card to absorb evidence overflow.
- The live region uses two columns: a flexible battle column and a contained decision rail. The battle column receives approximately 62–68% of the available width; the decision rail receives the remaining 32–38%.
- The decision rail is a vertical stack with an independently scrollable content area. Jev output remains above harness details so the selected action is visible without scrolling.
- The battle surface uses a bounded aspect ratio and centers the official renderer within its stage. Idle content fills the same bounded stage without creating an oversized empty canvas.

### Compact desktop: 900px–1279px

- Retain the two-column battle-plus-rail composition when the viewport can support it.
- Reduce shell padding, rail spacing, and nonessential header metadata.
- Keep Jev summary, validation, and submitted order visible in the rail; harness sections scroll or disclose.
- Never place Jev below the entire harness panel merely because the harness contains many candidates.

### Narrow screens: below 900px

- Stack battle first, Jev summary second, and harness summary third.
- Convert the right rail into compact cards with explicit disclosures.
- Keep the battle stage bounded by width and aspect ratio; do not use a desktop minimum height.
- The Inspect workbench becomes a full-width overlay/page region with a horizontally scrollable tab rail.

All layout dimensions use `min()`, `max()`, `clamp()`, `dvh`, and `aspect-ratio` where appropriate. No component may rely on a hard-coded height that exceeds the viewport at the supported desktop sizes.

## Component behavior

### Header

The header remains an operational bar rather than a marketing hero. At wide widths it may show format and battle tag; at compact widths those values collapse into the current state summary or remain available in Inspect. The start button keeps its existing behavior and truthful status text.

### Battle surface

The battle card owns the official renderer frame, battle message log, and renderer status. The custom shell may provide framing, origin labels, and connection/event treatment, but it must not paint a second battle scene. The stage receives a stable bounded size whether the state is idle, active, or complete.

### Jev decision summary

The summary is the primary right-rail focal point. Its hierarchy is:

1. response state;
2. returned selected action or explicit unavailable/fallback state;
3. returned confidence, if present;
4. returned probability map, if valid and present;
5. validation and submitted-order state;
6. compact reported metadata.

The summary must distinguish a provider response from an adapter fallback. A fallback is never styled or labeled as Jev's selected action.

### Harness summary

The default harness card answers “what public state and legal decision space did the application provide?” It shows concise fact rows and counts. Calculated facts and the complete legal-action set live in a contained disclosure or Inspect tab, with independent scrolling. It must preserve source labels and unknown markers.

### Lifecycle strip

The lifecycle strip is a horizontal event indicator derived from actual state. Completed stages are stable, the active stage receives a restrained pulse, and failed/fallback stages use an explicit label plus non-color marker. It must not invent per-stage durations where the telemetry does not record them.

### Decision history

History remains a compact rail of Jev decision records and adapter outcomes. It must not become a second battle log. Cards animate in only when a new record appears and open the selected record in Inspect.

## Visual language

Use a restrained battle-client aesthetic built from CSS and existing renderer content:

- graphite operational chrome;
- warm neutral surfaces that do not clash with Showdown terrain/weather;
- distinct but muted accents for Showdown, Harness, Jev, and fallback/adapter states;
- stronger contrast between primary decision, supporting facts, and raw technical evidence;
- generous but bounded battle-stage space instead of large unstructured page whitespace;
- small origin labels that are semantic and readable, not decorative noise.

Do not add generated artwork, a second Pokémon scene, cyberpunk styling, marketing slogans, or decorative charts without a recorded metric behind them.

## Motion and accessibility

Allowed motion:

- live connection indicator pulse while connecting;
- lifecycle active-stage pulse;
- selected decision reveal after a turn event;
- probability bars filling from zero when a valid map arrives;
- history card entrance when a new record is appended;
- fallback/error emphasis when a degraded event arrives.

Every motion effect has a stable non-animated equivalent. `prefers-reduced-motion: reduce` disables movement while retaining labels, borders, icons, and state. Focus indicators remain visible. Inspect tabs use real buttons with `role="tab"`, selected state, keyboard arrow navigation, and a labeled panel. Disclosure controls use native or equivalent accessible expanded state.

## Data and implementation boundaries

The redesign is frontend-focused:

- `src/jev_showdown/web/static/index.html` owns the Live/Inspect shell and progressive-disclosure markup.
- `src/jev_showdown/web/static/style.css` owns viewport sizing, responsive layout, visual hierarchy, and motion.
- `src/jev_showdown/web/static/dashboard/render.js` owns compact summaries, disclosure state rendering, lifecycle/history presentation, and event animation hooks.
- `src/jev_showdown/web/static/dashboard/inspector.js` owns the Inspect workbench behavior and tab accessibility.
- `src/jev_showdown/web/static/dashboard/app.js` owns mode/open-close interactions and preserves existing WebSocket actions.
- `src/jev_showdown/web/static/dashboard/charts.js` and `state.js` remain data-format helpers unless a focused UI issue requires a small change.
- Backend projection and telemetry contracts remain unchanged unless tests demonstrate a missing browser-safe field required by an already-authorized view.

## Verification and acceptance criteria

The implementation is ready for review only when all of the following are demonstrated:

- At 1440x900, the Live view presents the battle, current Jev decision, validation/submission state, lifecycle strip, and history header without the battle stage stretching to the full height of the evidence content.
- At 1280x800, the battle and Jev summary remain visible while harness details scroll or disclose.
- At 1024x768, Jev does not fall below an unbounded harness column.
- At a narrow viewport, the stack is readable and does not introduce horizontal page overflow.
- A populated recorded turn renders actual choice, confidence, probabilities, legal-action count, and validation state without fabricated values.
- Fallback, provider error, invalid probability, and completed-battle states remain explicit and attributable.
- Inspect opens from the header and history/context actions, supports keyboard tab navigation, preserves selection, and exposes the redacted structured evidence.
- The official renderer remains the only battle UI and remains integrated through the existing frame/replay path.
- Reduced-motion mode keeps all state readable without animation.
- Existing Python tests pass, focused frontend/browser checks pass, and fresh screenshots are inspected at representative desktop and compact viewports.

## Non-goals

- Replacing the Showdown renderer.
- Adding new gameplay controls.
- Changing Jev prompts, provider selection, or decision semantics.
- Adding backend metrics solely to make the UI look more complete.
- Rewriting unrelated project documentation or source modules.
