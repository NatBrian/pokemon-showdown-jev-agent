# Jev Showdown Dashboard UI/UX Design

Status: approved design direction; artifact-verified visual specification for low-fidelity prototyping

This document defines the proposed visual and interaction design for the public-facing Jev Showdown dashboard. It describes the screen composition, evidence hierarchy, component behavior, rendering rules, visual language, animation, chart usage, assets, responsive behavior, and prototype states.

The dashboard is an observatory around one real autonomous Pokémon Showdown battle. The live battle remains the primary visual surface. The dashboard makes the application pipeline understandable by showing what Showdown provided, what the harness calculated, what Jev received and returned, what the adapter validated and submitted, and what Showdown subsequently observed.

This document is a visual and interaction design specification. The [dashboard product contract](dashboard-product-contract.md) remains the authority for product truth, data provenance, behavior, and integrity.

The data mapping in this document has been checked against the latest complete evaluation artifact, `artifacts/foul-play-evaluation-post-history-fix-10s-2026-09-21`. That run contains 77 Jev API-call records, 84 Jev event records, and the corresponding Showdown battle logs. The artifact is an evidence fixture for the rendering contract, not a set of values to hard-code into the UI.

The previously generated dashboard PNG mockup was intentionally discarded because its layout contained inaccurate sample values and inconsistencies. It is not an implementation reference; this markdown and the verified artifacts are the sources of truth for the real dashboard.

## 1. Design intent

The dashboard should let two audiences understand the same live turn:

- A non-technical viewer should understand that a real battle is happening, that the system is observing it, that Jev receives a bounded decision problem, that Jev chooses an action, and that the action is sent back into Showdown.
- A technical viewer should be able to inspect the exact state snapshot, calculated candidates, request, response, validation, submitted order, protocol evidence, timing, and fallback behavior.

The design should make those two experiences coexist. The default view should not be a wall of JSON, but the structured evidence should always be one deliberate interaction away.

The dashboard should feel like the official Showdown battle experience gained a transparent observer layer and a restrained Pokémon-game arcade treatment: precise, observable, playful, and visually attractive without becoming a marketing page or an invented AI control room.

## 2. Core design principles

### 2.1 Battle first

The official Showdown battle surface is the visual anchor. Pokémon, HP, teams, battle scene, effects, messages, and battle outcome remain owned by the official renderer. The surrounding dashboard must not redraw or duplicate those elements.

### 2.2 Make the system boundary visible

The UI must distinguish four origins:

| Origin | Visual responsibility |
| --- | --- |
| Showdown | Official battle presentation, public protocol state, and observed result |
| Harness | Extracted public state, deterministic calculations, legal candidates, uncertainty, timing, request metadata |
| Jev | Fields actually returned by Jev: typed choice, confidence, probabilities, model, usage, cost, latency, and errors |
| Adapter | Validation, selected legal order, fallback selection, submitted-order message, and submission state |

Every panel that could confuse these sources gets an explicit origin label. The origin label is a semantic badge, not decorative text.

### 2.3 Show the decision boundary, not hidden reasoning

The design makes Jev understandable by showing:

- the bounded candidate set sent to Jev;
- the typed question and criteria;
- the returned choice;
- returned confidence and probabilities when available;
- model, usage, cost, and timing metadata when recorded;
- validation and adapter submission.

The design never presents fabricated chain-of-thought, invented prose explanations, win probability, psychology, hidden reasoning, or a locally generated rationale as if it came from Jev.

### 2.4 Every raw object gets a visual summary

All structured data remains inspectable, but the default presentation translates it into visual summaries:

- state objects become labeled fact rows;
- candidate maps become legal-action rows and comparison bars;
- Jev probabilities become horizontal bars;
- timing fields become duration tiles and waterfalls;
- event records become decision cards;
- captured protocol messages become parsed evidence rows with expandable raw frames; otherwise the UI shows the captured request/order fields and says that raw frames were not recorded.

Raw JSON is available through technical inspection, not forced into the primary view.

### 2.5 No visual element without an observable question

Charts and effects must explain a real relationship in the live data. The UI should not show decorative gauges or fabricated “AI intelligence” scores.

## 3. Overall composition

The primary layout is a desktop observatory with two live regions:

1. Official live battle surface.
2. A decision rail containing the Jev decision panel above the System Harness evidence panel.

Decision history and current-turn flow occupy horizontal bands beneath those zones. Technical inspection opens as a full-viewport workbench from the top-bar view switcher.

Implementation note: the current live shell supersedes the earlier three-column sketch below with a bounded two-column desktop layout. The live battle occupies the primary column; the decision rail owns the secondary column and scrolls its Jev and Harness cards independently. Inspect is a full-viewport technical workbench selected from the top-bar view switcher.

### 3.1 Target viewport

The first low-fidelity prototype should target:

- Primary: 1440×900.
- Supported landscape: 1280×800.
- Compact landscape fallback: 1024×768 with tighter spacing and collapsible evidence sections.

The main experience should not require excessive scrolling at any of these desktop sizes.

### 3.2 Desktop grid

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ TOP STATUS BAR                                                             │
├───────────────────────────────┬──────────────────────┬──────────────────────┤
│                               │                      │                      │
│                               │                      │                      │
│       LIVE SHOWDOWN           │   SYSTEM HARNESS     │        JEV           │
│       BATTLE SURFACE          │   observe            │   decision status    │
│       official renderer       │   calculate          │   selected action    │
│                               │   legal actions     │   probabilities      │
│                               │   Jev handoff       │   validation/output   │
│                               │                      │                      │
├───────────────────────────────┴──────────────────────┴──────────────────────┤
│ CURRENT-TURN EVIDENCE STRIP                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ DECISION HISTORY                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Recommended live-region proportions:

- Battle surface: approximately 64% at the primary desktop target.
- Decision rail: approximately 36%, with Jev above Harness.

The battle width should remain large enough for the official renderer to retain its visual clarity. The evidence panels should be narrow enough to feel like instrumentation but wide enough to render structured data without constant truncation.

### 3.3 Vertical layout

- Top status bar: 56–64px.
- Main content region: approximately 620–670px at a 900px viewport.
- Current-turn evidence strip: 72–96px.
- Decision history: 120–160px.

If content exceeds the available height, the evidence panels scroll independently before the battle surface does. The battle should remain visually stable while the viewer inspects harness or Jev details.

## 4. Top status bar

The header is a compact operational bar, not a hero banner.

### 4.1 Left group: identity

Display:

- Product name: `Jev Showdown`.
- Small connection indicator.
- Format: `Gen 9 Random Battle`.
- Battle identifier or shortened room tag.

The battle identifier should be monospaced and copyable from the technical inspection path, but not visually dominant.

### 4.2 Center group: current lifecycle state

Display one truthful current state:

```text
OBSERVING
CALCULATING
JEV EVALUATING
LEGAL
ORDER SUBMITTED
AWAITING SHOWDOWN
RESULT OBSERVED
```

The state can include a short secondary description:

```text
JEV EVALUATING
Waiting for typed provider response
```

The label must represent the application’s actual state. It must not say “Jev thinking” during local calculation or Showdown wait time.

### 4.3 Right group: controls and status

Idle state:

- Primary button: `Start Jev Battle`.
- Secondary status: `Ready`.

Active state:

- Disabled or replaced action: `Battle running`.
- Connection status.
- Current turn.
- Optional battle elapsed time.

Completed state:

- `Battle complete`.
- Replay link when available.
- `Inspect final decision`.

No manual move, manual order, battle setup, replay editing, or multi-battle orchestration controls belong in this header.

## 5. Live Showdown stage

### 5.1 Role

The live battle stage is the primary viewer experience. It should preserve the official renderer and its native visual language.

### 5.2 Frame

Place the renderer inside a stable frame with:

- A thin border.
- A small `SHOWDOWN` origin badge in the frame header.
- Optional room/battle label.
- Connection or loading state outside the renderer when possible.
- No permanent dashboard overlays covering Pokémon, HP bars, or battle messages.

The frame should visually separate the official battle from the observability panels without making it feel like an embedded web page inside another web page.

### 5.3 Loading and connection states

Before a battle starts, show a quiet state inside the stage:

```text
SHOWDOWN BATTLE SURFACE
Ready to start an autonomous battle
```

During connection:

```text
Connecting to Showdown
Waiting for battle room
```

If the connection drops, show a non-blocking warning strip at the top or bottom edge of the stage. Keep the last known renderer visible if the application still considers it valid, but label the state as stale or reconnecting.

### 5.4 Boundary rule

Do not add a second team display, duplicate HP display, duplicate weather display, duplicate battle message log, or duplicate outcome card outside the official renderer. Dashboard metrics can reference the battle, but must not compete with it as another game surface.

## 6. System Harness panel

The harness panel is the primary explanation of what the application is doing.

### 6.1 Panel header

```text
SYSTEM HARNESS
TURN 08
CALCULATING
HARNESS
```

Header content:

- `SYSTEM HARNESS` title.
- Current turn.
- Current lifecycle state.
- Origin badge.
- Small timing value when available.
- Expand/collapse control for individual sections.

### 6.2 Section A: public state observed

This section summarizes what the harness extracted from Showdown.

Display as labeled rows grouped into compact categories:

```text
RUN CONTEXT
Format               gen9randombattle
Battle               battle-gen9randombattle-56
Turn                 1

REQUEST
Type                 move
Showdown rqid        3
State version        1
Harness schema       2

OBSERVED STATE
Self active          Dragalge · L88 · HP 100%
Opponent active      Swampert · L83 · HP 100%
Self team slots      6 observed
Opponent slots       1 revealed · 5 unknown
Tera available       Yes
Weather              None observed
```

The values above are an artifact fixture showing the current field mapping. In the running dashboard, every value is populated from the current `snapshot` and `request` objects. The official renderer remains the owner of the visible team and HP presentation; this panel exposes the harness state and its provenance without creating a duplicate battle UI.

Every value that originated from Showdown gets a `SHOWDOWN` source badge or a source marker in the section header.

Unknown and unavailable values should be explicit:

```text
Opponent item        Unknown
Exact stats          Not available
Damage assumptions   Partial
```

### 6.3 Section B: deterministic calculations

Show calculations as concise fact rows with assumption labels.

Example:

```text
Dracometeor (Tera)           move_dracometeor_tera
Base power / category        130 · SPECIAL
Type / effectiveness          DRAGON · 1.0× calculated
Heuristic relative estimate  66–78 inferred
Accuracy / PP / priority     90% · 8 · 0
Damage / KO                  Unknown · Unknown
```

Use `Calculated by Harness` as the section origin. Use `Estimate` or `Range` wherever the value depends on unknown items, abilities, EVs, IVs, or exact stats.

Visual treatments:

- Small calculation cards.
- Type-effectiveness chips.
- Heuristic-relative-range bars with minimum and maximum markers; never label these as damage or win probability.
- Assumption badges.
- A neutral unknown icon for missing inputs.

Do not turn deterministic annotations into a fabricated global score such as “battle advantage,” “risk,” or “win chance.”

### 6.4 Section C: legal action set

This section is one of the most important harness visuals because it establishes Jev’s bounded decision space.

Each candidate is shown as a row:

```text
✓  Dracometeor                   move_dracometeor
✓  Dracometeor + Tera             move_dracometeor_tera
✓  Dragontail                    move_dragontail
✓  Focus Blast                   move_focusblast
✓  Switch to Emboar              switch_emboar
…  8 more legal candidates
```

The artifact fixture above had 13 legal candidates. The recorded runs vary from 1 to 13 candidates, so the UI must render the current count and never hard-code `9`. The action list is sourced from `snapshot.legal_actions`; the Jev question criteria are sourced from `jev_request.questions.action.criteria` and are reconciled by candidate ID.

Candidate row fields may include:

- Type-effectiveness chips such as `2×`, `½×`, or `Immune`, when calculated.
- Move-category icons for physical, special, or status actions, when available.
- Move type and category labels.
- Tera or switch markers.
- Human-readable action.
- Stable candidate ID.
- Action class: move, switch, tera variant.
- Legal state.
- Important calculated facts.
- Whether the candidate is included in the Jev request.
- Whether it was later selected.

Move candidates expose the recorded facts when present: `base_power`, `category`, `type`, calculated `type_multiplier`, `accuracy`, `pp`, `priority`, `tera`, and the inferred `utility_estimate` range. `damage` and `ko` are explicitly unknown in the verified fixture. Switch candidates expose `hp_fraction`, `status`, and the unknown `entry_hazard_damage` and `opponent_coverage` consequences. These are not interchangeable metrics.

These are annotations from the harness or Showdown state. They must not imply a strategic recommendation that the harness did not calculate.

Use text and icons in addition to color:

- `LEGAL` with a check icon.
- `DISABLED` with a slash icon.
- `SELECTED` with a filled marker.
- `NOT SENT` with a neutral label.

### 6.5 Section D: Jev handoff packet

The handoff is rendered as a compact bridge between Harness and Jev rather than as a duplicate full input panel.

```text
JEV INPUT READY
13 legal candidates
1 typed choice question
Harness schema 2
Showdown rqid: 3
State version: 1
```

Additional summary values:

- Public-state field count.
- Deterministic annotation count.
- Candidate count.
- Uncertainty marker count.
- Criteria count.
- `can_tera` and request type.
- Request start and finish timestamps when the API-call record is available.

Do not show payload size unless the dashboard measures serialized size itself and labels it `derived`. The current artifacts do not record a payload-size field. Do not combine `rqid`, `state_version`, `call_id`, and the internal fingerprint request ID into one invented request ID; show each identifier with its source label.

Controls:

- `View structured input` expands a readable summary.
- `Inspect raw request` opens the technical drawer.

This is the only primary-view representation of the Jev input. The Jev panel may show `Received N legal candidates`, but it should not duplicate the full request.

## 7. Jev panel

The Jev panel is visually strong and immediately legible. It should make the actual returned decision the focal point of the right side.

### 7.1 Panel header

```text
JEV
jev-1.13-free
RESPONSE RECEIVED
MODEL REPORTED BY JEV
```

The verified records contain `model: jev-1.13-free` and run metadata contains the configured Jev endpoint. They do not contain a provider display name such as `OpenCode System One`; do not invent one. Show the endpoint only in technical run metadata, subject to normal redaction rules.

Possible states:

- `READY`.
- `REQUESTING`.
- `RESPONSE RECEIVED`.
- `INVALID RESPONSE`.
- `TIMEOUT`.
- `FALLBACK USED`.
- `UNAVAILABLE`.

### 7.2 Decision hero

When Jev returns a valid typed choice:

```text
JEV SELECTED

Dracometeor + Tera
move_dracometeor_tera
```

The hero includes:

- Large action label.
- Stable candidate ID.
- `JEV OUTPUT` origin badge.
- Returned confidence, when available.
- Validation state.
- Submitted order, once the adapter submits it.

Example:

```text
Returned confidence     0.94
Validation              Passed
Submitted order         /choose move dracometeor terastallize
```

The values above are a valid-response fixture from the verified artifact. The running view must use the returned `choice`, `confidence`, and `submitted_order.message` for the selected record.

Do not use `best move` unless the real response explicitly provides that semantics. Prefer `Jev selected`.

### 7.3 Probability bars

Returned candidate probabilities appear as horizontal bars.

```text
Dracometeor + Tera       █████████████████ 96%
Dracometeor              █                  1%
Focus Blast + Tera       █                  1%
Switch to Emboar         █                  1%
```

Rules:

- Display only values returned by Jev.
- Show exact numeric values on hover, focus, or technical expansion.
- Keep all returned candidates available through scrolling or expansion.
- Highlight the selected candidate but do not visually erase alternatives.
- Use the returned candidate IDs as the distribution domain; do not add an `Other legal actions` bucket unless Jev actually returns one.
- If the response has invalid probabilities, show the validation error instead of silently “fixing” the values in the primary evidence view.
- If probabilities were not returned or the normalized response is empty because validation failed, show `Not returned` or `Rejected by validation`. Keep any raw provider map inside the raw response view, clearly marked as rejected.

### 7.4 Confidence indicator

Use a ring or horizontal meter only for returned confidence. Label it explicitly:

```text
RETURNED CONFIDENCE
85%
```

Never label it `win probability`, `success chance`, `battle odds`, or `decision quality` unless those are real returned fields.

### 7.5 Jev metadata

Render provider metadata as compact tiles or a two-column fact grid:

```text
Model             jev-1.13-free
Jev latency       1.72s
Wrapper latency   1.72s
Input tokens      22,728
Output tokens     171
Reported cost     0
```

The panel should visually separate returned Jev fields from local wrapper measurements. For example:

- `Returned or normalized from Jev`: choice, confidence, probabilities, usage, cost, response latency, model, and error.
- `Measured by the request wrapper`: `started_at`, `finished_at`, and `wrapper_latency_ms`.
- `Measured by the decision event`: `validation.latency_ms` when present. The current artifact does not provide separate calculation, validation, or submission durations.
- For error/fallback records, do not interpret zero token counts or an empty probability object as a successful zero-usage response; show the actual error state.

### 7.6 Invalid response and fallback

If Jev fails validation:

```text
JEV RESPONSE INVALID
Probability sum must equal 1.0

ADAPTER FALLBACK
First legal candidate

Validation: Fallback legal
Submitted: /choose move shadowball
```

Recorded fallback reasons include provider HTTP 503, a Jev request timeout after the 10-second limit, and one invalid probability sum. The fallback action and exact reason must come from `fallback_reason`, `validation`, and `submitted_order`; never replace them with a generic success message.

Fallback must be visually distinct and remain visible until the next state transition. It must not look like a normal Jev choice.

### 7.7 Viewer-friendly copy rules

The interface may use concise, game-like presentation, but its copy must stay within observable evidence. Good labels include:

- `JEV SELECTED`
- `RETURNED CONFIDENCE`
- `LEGAL CANDIDATES`
- `VALIDATION PASSED`
- `ORDER SUBMITTED`
- `RESULT OBSERVED`

Do not use entertaining but unsupported claims such as:

- `Jev outsmarted the opponent`.
- `Jev predicts victory`.
- `Perfect tactical play`.
- `Jev is thinking deeply`.
- `This move will win`.

The dashboard can make a real response feel exciting through typography, selection frames, probability bars, and motion. It must not make the response appear more certain or more strategic than the returned data supports.

The recorded Jev question instruction is `Choose the strongest legal action that maximizes win probability.` This is an input instruction, not a measured win probability and not evidence that Jev predicted victory. It may be shown verbatim in the technical `Jev input` view, but the primary dashboard must continue to label the output as `Jev selected` and `Returned confidence`.

## 8. Current-turn evidence strip

The strip below the primary panels represents the current turn’s processing pipeline. It is not the history timeline.

```text
✓ OBSERVE → ✓ CALCULATE → ✓ OPTIONS → ✓ JEV DECIDES → ✓ VALIDATE → ✓ ACT → ◷ RESULT
```

Each stage displays:

- State label.
- Status icon.
- Duration or result summary where available.
- Expandable detail.

Example:

```text
OBSERVE       State captured
CALCULATE     Facts available
OPTIONS       13 legal
JEV DECIDES   1.72s
VALIDATE       Passed
ACT            /choose move dracometeor terastallize
RESULT         Awaiting Showdown
```

Only the active stage receives a subtle animated treatment. Completed stages use a stable check indicator. Failed stages remain visible with an explanatory label. `OBSERVE`, `CALCULATE`, and `OPTIONS` are derived display stages from the captured snapshot and legal-action records; they must not show invented millisecond values. The verified artifacts record request/response timestamps, wrapper latency, and decision/validation latency, but not separate extraction, calculation, validation, or submission durations.

## 9. Decision history

The decision history sits at the bottom of the page as a compact horizontal rail.

Each record is a decision and adapter-action summary, not a second battle log.

### 9.1 Decision card

```text
TURN 08
Dracometeor + Tera
Jev output
94% confidence · 1.75s
Submitted
```

The displayed action, confidence, and latency are record-backed values. For example, the verified first decision used `move_dracometeor_tera`, returned confidence `0.94`, and recorded decision latency `1754ms`; the card must not use these values for every turn.

The turn label is styled as a compact pixel-arcade badge: a short, high-contrast marker with a stepped border or segmented edge. It identifies the battle turn and gives the history rail a game-like rhythm; it is not a score, rating, win indicator, or performance grade.

Fallback example:

```text
TURN 09
First legal candidate
Fallback
HTTP 503 · 9.86s
Submitted
```

Record fields:

- Turn number.
- Selected action.
- Action class.
- Jev or fallback origin.
- Confidence when returned.
- Latency.
- Validation state.
- Submission state.
- Result state.
- Error or fallback marker.

For multi-battle runs, include the `battle_tag` on the card or in its expanded summary. A turn number alone is not globally unique. The current run has `battle-gen9randombattle-56`, `-57`, and `-58`.

### 9.2 History interaction

- Clicking a card loads the record into the technical inspection drawer.
- The current turn receives a stronger border.
- Fallback and error cards receive a persistent text marker.
- The rail can scroll horizontally without moving the battle stage.
- A compact table view can be offered to technical viewers.
- History resets when a new battle begins.
- History remains inspectable after a battle completes until the next battle starts.

## 10. Technical inspection drawer

The Inspect control opens a full-viewport technical workbench so the evidence surface can use the available width for readable raw records and comparison tables. The Live control is the explicit route back to the battle layout; the underlying live surface is kept mounted but hidden while inspection is active.

The workbench uses the full viewport on desktop and narrow screens so raw records and comparison tables remain readable; the Live tab provides the explicit return path.

### 10.1 Tabs

1. `Overview`
2. `Showdown request`
3. `Harness state snapshot`
4. `Calculated facts`
5. `Jev input`
6. `Jev response`
7. `Validation`
8. `Submitted order`
9. `Protocol evidence`
10. `Raw event`
11. `Run metrics`

### 10.2 Human-readable view

Each tab begins with a summary block before showing detailed fields.

Example:

```text
REQUEST
Battle tag              battle-gen9randombattle-56
Showdown rqid           3
Jev call ID             1
Model                   jev-1.13-free
Question type           choice
Candidate count         13
Harness state schema    2
Request state version   1
Unknown markers         Derived from source fields
Payload size            Not recorded
```

Use separate labeled identifiers when available: `battle_id`/`battle_tag`, Showdown `request.rqid`, request `state_version`, Jev API `call_id`, and the event fingerprint. Never synthesize them into one identifier.

### 10.3 Raw structured view

The raw view provides:

- Syntax highlighting.
- Expandable nested objects.
- Field search.
- Copy control.
- Field path display.
- Redaction labels.
- Origin labels where appropriate.

Raw payloads must be redacted before rendering. Never render authorization headers, credentials, or secrets.

The technical drawer uses a darker version of the same neutral Showdown-style shell: charcoal background, cream and muted-gray text, mustard Harness highlights, muted orchid Jev highlights, green Adapter confirmation, and coral errors. Do not make cyan or blue the default syntax color scheme; a blue or cyan value may appear only when it represents real Showdown or Pokémon-type data.

### 10.4 Protocol evidence

Render raw frames as parsed evidence rows:

```text
OUTBOUND  request record
Battle tag  battle-gen9randombattle-56
Order       /choose move dracometeor terastallize
Submitted by  Adapter
```

Each row expands to show the captured record. Include direction or record type, `started_at`/`finished_at` when available, battle identifier, request type, `rqid`, parsed order, and raw JSON. A raw websocket frame is shown only when a protocol-frame artifact is actually present. The verified latest Jev artifact has no separate Jev raw-frame stream or `protocol-replay.json`, so the UI must say `Raw protocol frame not captured` instead of implying that the parsed order is a raw frame.

## 11. Charts and visual analytics

Charts are supporting evidence. They should never displace the battle, current decision, or current adapter status.

### 11.1 Candidate probability chart

Horizontal bars show Jev’s returned distribution over legal candidates.

Primary question: `What did Jev return across the available legal actions?`

Render this chart only for a response that passed probability validation. If validation rejects the map, replace the bars with `Probability map rejected` plus the exact validation error, and expose the raw returned map only in the technical response view.

### 11.2 Latency waterfall

Use a small horizontal waterfall only for recorded boundaries:

```text
Jev response latency  1.72s
Wrapper latency       1.72s
Decision latency      1.75s
```

Each segment is labeled by source or subsystem. The current artifacts expose `response.latency_ms`, `wrapper_latency_ms`, and `validation.latency_ms`, plus API-call start/finish timestamps. They do not expose separate state-extraction, calculation, validation, or order-submission durations, so those segments are omitted rather than estimated.

### 11.3 Per-turn latency sparkline

Show decision latency across recent turns. Include:

- Turn labels.
- Actual latency points.
- Move timer threshold, if known.
- Fallback markers.
- Timeout markers.
- P50, P95, and P99 summary values when the run contains them.
- Hover/focus details.

The chart should answer whether decision timing is staying within the available move window. If the timer threshold is not captured, do not draw one. It must not imply that lower latency means stronger play. For the verified run, the recorded summary is P50 `1136.9ms`, P95 `10060.0ms`, and P99 `10465.2ms`; these belong to the run summary, not every individual turn.

### 11.4 Token and cost metrics

Use compact numeric tiles first:

```text
Input tokens      22,626
Output tokens        172
Reported cost          0
```

A small stacked bar may compare input and output tokens over recent turns if enough real records exist. Do not create a cost trend from missing or estimated values.

For error and fallback records, show the error first and mark token values as unavailable for billing/usage interpretation when the wrapper stored zeros. The presence of a numeric field is not proof that a successful provider response produced those tokens.

### 11.5 Battle-level reliability tiles

Useful live values:

```text
Battles completed  3
Jev calls          77
Valid choices      57
Fallbacks          20
Illegal actions    0
Stale responses    0
Provider errors    19
  HTTP 503         14
  Timeouts          5
Protocol errors     1
Timer failures      0
Latency P50       1.137s
Latency P95      10.060s
Latency P99      10.465s
```

The values above are the verified three-battle run summary. For a single battle, counts are more honest than percentages. Avoid implying statistical significance from a small sample. Keep provider errors, protocol validation errors, and deterministic fallbacks separate; they are different failure classes.

When the run audit reports a degraded or invalid evaluation status, show that status beside the tiles. The verified run completed technically but was `invalid for strategic comparison` because 20 decisions used deterministic fallback; do not present its 0–3 record as evidence of Jev strength.

### 11.6 Candidate comparison matrix

For technical viewers, provide an optional compact table:

| Candidate | Legal | Included | Jev probability | Selected | Submitted |
| --- | --- | --- | ---: | --- | --- |
| Dracometeor | Yes | Yes | 1% | No | No |
| Dracometeor + Tera | Yes | Yes | 96% | Yes | Yes |
| Dragontail | Yes | Yes | 0% | No | No |

This table belongs in the harness/Jev expansion or inspection drawer, not as the default dominant element.

### 11.7 Battle completion summary

After Showdown reports the result, show:

- Observed result.
- Turns played.
- Jev decisions.
- Fallback count.
- Provider errors.
- Replay link when available.
- Evidence availability.

The current battle-end events record `winner`, `won`, `total_turns`, and run counters. They do not record per-battle duration, so omit duration unless a future artifact adds start/end timestamps for each battle. The verified latest run completed battles 56, 57, and 58 at 21, 19, and 22 turns; FoulPostFix won all three. A replay was requested, but no replay file was present, so show `Replay unavailable` rather than a dead link.

Do not show a local prediction as a battle outcome.

## 12. Visual language

The approved direction is **Showdown Classic + Pixel Touch**.

The dashboard must not treat one battlefield background as the product theme. The supplied reference image shows a particular terrain/weather presentation inside the battle scene; that scenery can change from battle to battle. The stable dashboard identity belongs in the fixed client chrome around the scene: neutral panels, compact controls, HP/status-inspired indicators, dark battle-message surfaces, clear outlined labels, and dense but approachable information.

The visual system has three layers:

1. **Official battle layer:** the real Showdown renderer owns the changing battlefield, sprites, teams, HP, effects, messages, and result.
2. **Neutral Showdown-style shell:** the dashboard frame uses warm gray, cream, charcoal, and muted status colors so it remains compatible with every terrain and weather background.
3. **Pixel arcade treatment:** stepped corners, hard-edged borders, segmented bars, short pixel-display labels, and restrained game-like transitions add the original-Pokémon feeling without replacing the modern readability of Showdown.

The dashboard should look like a Pokémon battle client with an observability layer, not like a blue developer SaaS dashboard, a cyberpunk console, or a separate fan-made battle game.

### 12.1 Surface and color

The overall first impression should be neutral gray/cream/charcoal. Saturated colors are reserved for live battle data, semantic status, and small accents.

Recommended base palette:

| Role | Color | Use |
| --- | --- | --- |
| Warm gray page chrome | `#B9B9B3` | Outer dashboard background and inactive frame surfaces |
| Light panel | `#E8E7E0` | Harness and Jev panel bodies |
| Panel highlight | `#F5F3EA` | Raised rows, selected readable surfaces, empty states |
| Dark battle-log surface | `#282824` | Current-turn messages, dense evidence headers, technical console |
| Dark border | `#45453F` | Panel outlines, separators, pixel frames |
| Primary text | `#22221F` | Main text on light surfaces |
| Secondary text | `#686862` | Metadata and supporting labels |
| Cream text | `#F6F0D8` | Text on dark surfaces and battle-style callouts |
| Harness accent | `#D7A936` | Deterministic calculations, legal-action handoff, harness status |
| Jev accent | `#B47CB8` | Returned decision, provider response, Jev-specific emphasis |
| Adapter success | `#6FA36A` | Legal validation and submitted-order confirmation |
| Warning/fallback | `#D5963E` | Timeout, fallback, degraded provider state |
| Error | `#C95F55` | Invalid response, provider failure, validation error |

Blue is not a dashboard foundation color. It may appear only when a real Showdown or Pokémon-type value requires it; it must not dominate the page background, panel surfaces, borders, or primary accents.

Use color together with text, icons, borders, or shapes. For example:

- `HARNESS` plus an ochre stripe and calculation icon.
- `JEV OUTPUT` plus an orchid stripe and response icon.
- `FALLBACK` plus an amber stripe, warning icon, and explicit text.
- `VALIDATION PASSED` plus a green check and text.

### 12.2 Panel and control styling

Use the visual grammar of a polished Pokémon battle client:

- Warm gray or cream panel bodies.
- Dark charcoal section headers and message surfaces.
- One- or two-pixel dark outlines.
- Small bevels or inset highlights.
- Squared, clipped, or gently rounded corners rather than large pill cards.
- Compact rectangular buttons inspired by move and switch controls.
- Segmented progress bars inspired by HP and PP displays.
- Pixel-like badges with a clear text label.
- Shallow shadows; no floating glassmorphism stack.

The Harness panel uses an ochre/gold origin stripe. The Jev panel uses a muted orchid origin stripe. Both panels remain mostly neutral so the accent communicates provenance instead of turning each panel into a different colored theme.

Use the dark battle-message surface for short, high-attention callouts such as `JEV SELECTED`, `ORDER SUBMITTED`, and `RESULT OBSERVED`. Use light neutral surfaces for fact rows, candidate lists, and technical summaries.

### 12.3 Pixel arcade treatment

The pixel influence should be visible but controlled:

- Use an 8px spacing rhythm for major layout measurements.
- Use stepped corners or clipped corner details on outer frames.
- Use hard-edged one- or two-pixel outlines rather than soft glowing borders.
- Render probability and timing bars as discrete pixel segments while preserving exact numeric labels.
- Use small bitmap-like icons for observe, calculate, request, validation, fallback, and result.
- Use short pixel-display labels for `TURN 08`, `JEV SELECTED`, and lifecycle states.
- Reserve scanline or pixel-grid texture for a very low-opacity background treatment, never behind dense text.
- Keep battle-style text shadows or outlines for short labels, not entire paragraphs.

Do not use:

- A dominant blue gradient.
- Neon cyberpunk glow.
- Full-screen CRT distortion.
- Heavy scanlines that reduce contrast.
- Oversized 8-bit headings that make the interface difficult to read.
- Decorative pixel art that competes with the real Pokémon battle.

### 12.4 Typography

- Use a readable, compact sans-serif for normal interface text, action names, explanations, and dense evidence rows.
- Use a monospaced font for candidate IDs, request IDs, JSON, protocol commands, timestamps, and numeric telemetry.
- Use a licensed pixel or bitmap-style display face only for short labels, state names, and turn markers.
- Use large type for the current selected action, but keep the action name readable at a glance.
- Use small uppercase labels for origin and lifecycle states.
- Avoid using a pixel font or monospace font for paragraphs, raw tables, or every visible field.
- Use text outlines or shadows only where they improve the battle-style label treatment.

### 12.5 Density

The dashboard should be information-dense but not visually noisy.

- Use compact rows for telemetry.
- Group fields into named sections.
- Hide secondary fields behind disclosure controls.
- Keep one dominant focal point per panel.
- Use whitespace between evidence groups, not between every individual value.

## 13. Animation and effects

Animation communicates real state changes and data transfer while borrowing the discrete feel of a pixel arcade interface.

Use:

- A small stepped pulse while a Jev request is active.
- A short pixel-segment connector from Harness to Jev when the request is sent.
- Probability bars filling in discrete segments when a valid response arrives.
- A brief lock-on or selection-frame effect around the returned action.
- Green confirmation when validation passes and the order is submitted.
- Amber interruption treatment for fallback.
- Red but restrained treatment for provider or validation errors.
- A small activity marker on the current lifecycle stage.
- A short reveal transition for new decision-history cards.

Avoid:

- Constant particle effects.
- Excessive neon glow or blue ambient lighting.
- Fake AI-brain animations.
- Typewriter-style invented reasoning.
- Large loading modals covering the battle.
- Animations that suggest access to hidden Jev thought.
- Persistent CRT distortion or scanline movement.

All effects must have a static equivalent for reduced-motion users. Use `prefers-reduced-motion` to disable movement while preserving state, color, labels, and icons.

## 14. Asset strategy

The main dashboard does not require generated image assets. The official renderer supplies the important visual material, and the pixel treatment can be built from CSS, SVG, typography, and real data.

Use:

- The official Showdown renderer and its supplied assets.
- Existing Pokémon sprites provided by the renderer.
- Simple SVG or CSS pixel-style icons for observation, calculation, request, network, validation, code, warning, and result.
- Minimal arrows or connectors for the observable data flow.
- A licensed pixel-display font for short labels, with a readable fallback.
- CSS backgrounds, restrained gradients, borders, shadows, and neutral pixel textures.
- CSS-built panel corners, outlines, segmented bars, and origin badges.

Optional image assets may be considered later only for non-battle states:

- Idle/ready background texture.
- Neutral connection-state background.
- Neutral loading background.
- Small decorative pixel frame ornaments.

These optional assets must remain low contrast and must not introduce a second Pokémon battle scene.

Do not add:

- Duplicate Pokémon artwork outside the battle surface.
- AI-generated Pokémon illustrations.
- Generated terrain or weather backgrounds behind the live battle.
- Decorative mascots.
- Marketing hero artwork.
- Fake AI-brain visuals.
- A second battle client.

Icons should support semantic interpretation, not act as decoration. Every important icon also gets a text label or accessible name.

### 14.1 Visual regression guardrails

Before accepting a prototype, review it at a normal landscape viewport and ask:

- Is the first color impression warm gray, cream, charcoal, and real battle color, not blue?
- Does the live battle remain the most visually important area?
- Does the pixel treatment feel like an added Pokémon-game layer rather than a separate theme?
- Do the Harness and Jev accents communicate provenance without turning the panels into unrelated color worlds?
- Can a non-technical viewer read the current action and system state immediately?
- Can a technical viewer reach exact payloads and metrics without the primary view becoming raw JSON?
- Do animation and visual effects correspond to real events?
- Does the shell remain visually compatible when the battle terrain changes?

## 15. Runtime states and low-fidelity prototypes

The prototype set should include the following screens or state variations.

### 15.1 Idle / ready

- Official battle stage shows a neutral ready state.
- Harness panel shows `Waiting for battle`.
- Jev panel shows `No decision yet`.
- Header contains `Start Jev Battle`.
- History rail is empty with a short explanation.

### 15.2 Connecting

- Header shows `CONNECTING`.
- Battle stage shows connection progress.
- Harness panel shows `Waiting for public battle state`.
- Jev panel remains inactive.
- No fake decision data appears.

### 15.3 Battle active: observing

- Official renderer visible.
- Harness public state section populated.
- Current-turn strip highlights `OBSERVE`.
- Jev panel indicates `Waiting for harness input`.

### 15.4 Harness calculating

- Harness header highlights `CALCULATING`.
- Calculated facts animate in only as real events arrive.
- Legal action section updates.
- Current-turn strip highlights `CALCULATE` and `OPTIONS`.
- Jev panel shows `Waiting for request`.

### 15.5 Jev request in progress

- Handoff packet changes to `REQUEST SENT`.
- Connector animation moves from Harness to Jev.
- Jev panel shows `REQUESTING`.
- The relevant request identifiers (`rqid`, `state_version`, and `call_id`) and candidate count remain visible with source labels.
- No selected action is shown yet.

### 15.6 Valid Jev response

- Jev decision hero reveals the returned choice.
- Probability bars animate into their returned values.
- Confidence indicator appears only if returned.
- Validation begins as a separate stage.
- Harness panel retains the legal candidate set for comparison.

### 15.7 Validation and order submission

- Jev panel shows `VALIDATION PASSED`.
- Adapter action appears with exact submitted order.
- Current-turn strip highlights `ACT`.
- A small green confirmation indicates submission, without hiding the battle.

### 15.8 Awaiting Showdown result

- Header shows `AWAITING SHOWDOWN`.
- Submitted order remains visible.
- Result section shows `Waiting for observed update`.
- The dashboard does not infer damage, status, faint, or outcome before Showdown reports it.

### 15.9 Invalid Jev response / fallback

- Jev panel changes to `INVALID RESPONSE`.
- Error text states the actual validation reason.
- Adapter fallback appears in a separate block.
- Fallback action is marked `FALLBACK`, not `JEV OUTPUT`.
- Submitted fallback order is visible.
- History card preserves the fallback reason.

### 15.10 Provider timeout or error

- Jev panel shows provider status and timeout/error state.
- Harness and adapter panels remain visible.
- Fallback path is explicit.
- The dashboard does not replace the error with a generic successful-looking state.

### 15.11 Battle completed

- Showdown result remains visible in the official renderer.
- Header shows `RESULT OBSERVED`.
- Jev panel shows the final decision record.
- History remains inspectable.
- Completion summary shows real battle metrics and replay link when available.

### 15.12 Technical inspection open

- Right-side drawer overlays or compresses only the evidence side.
- Battle remains partially visible at desktop widths.
- Selected turn is clearly identified.
- Tabs expose human-readable and raw views.

### 15.13 Narrow landscape viewport

At 1024×768:

- Battle stage remains first.
- Harness and Jev panels become independently scrollable or switch to a two-tab evidence column.
- Current-turn evidence strip remains visible.
- History becomes horizontally scrollable.
- Technical inspection becomes a full-height drawer.

The implementation must not create a second battle view as a workaround for limited space.

## 16. Interaction model

Allowed primary interactions:

- Start the autonomous battle.
- Expand or collapse evidence sections.
- Inspect the current turn.
- Select a decision-history record.
- Open structured request/response data.
- Open technical inspection.
- Copy IDs, protocol commands, or structured values.
- Open an available replay link after completion.

Not allowed:

- Manual move selection.
- Manual order submission.
- Controls that imply the viewer is playing the battle.
- Fabricated strategy toggles.
- Unapproved settings or multi-battle orchestration.

## 17. Accessibility and semantics

- Use semantic buttons for expandable sections and inspection controls.
- Use headings to structure battle, harness, Jev, adapter, and inspection content.
- Announce lifecycle changes through an appropriate live region.
- Ensure fallback, error, and validation state are conveyed with text and icons, not color alone.
- Preserve keyboard focus when opening and closing the inspection drawer.
- Keep focus visible.
- Provide accessible names for icons and charts.
- Provide tabular or text alternatives for every chart.
- Respect reduced motion.
- Maintain sufficient contrast for text, borders, status indicators, and chart labels.

## 18. Data integrity requirements for rendering

The rendering layer must follow these rules:

- Render real live values in the active path.
- Omit unavailable values or label them as unavailable.
- Keep unknown opponent information unknown.
- Label deterministic calculations as calculations or estimates.
- Display returned Jev metadata only when returned or measured by the application.
- Never manufacture confidence, probabilities, cost, usage, risk, win chance, or reasoning.
- Render candidate legality from the current harness `legal_actions` snapshot, but distinguish it from adapter validation; never show an action as selected/submitted until current validation succeeds.
- Never show an order as submitted until the adapter submits it.
- Never show a result as observed until Showdown produces the corresponding update.
- Redact credentials before data enters the UI.

### 18.1 Artifact-verified data contract

The latest complete artifact provides the following renderable evidence.

Harness and state input per decision:

- `snapshot` with `battle_format`, `state_schema`, `turn`, `weather`, `can_tera`, `fields`, `side_conditions`, `history`, `glossary`, `self`, `opponent`, `beliefs`, `strategic_hypotheses`, `opponent_responses`, `legal_actions`, and the Showdown `request` object.
- `request` fields: `battle_id`, `rqid`, `request_type`, `turn`, `state_version`, `force_switch`, `maybe_trapped`, `trapped`, `wait`, and the captured deadline value.
- `legal_actions` facts: action ID, label, kind, move category/type/base power, type multiplier, accuracy, PP, priority, Tera marker, heuristic-relative estimate, and explicit unknown damage/KO values for moves; switch HP/status and unknown hazard/coverage consequences for switches.
- Provenance-bearing beliefs and hypotheses, including `observed`, `inferred`, and `unknown` source states, confidence values, units, and assumptions. Unknown opponent slots and unrevealed set details remain unknown.
- Recent action history, opponent-response summaries, and the glossary are available in the structured state view. They are summarized in the primary view only when they answer a current-turn question.

Jev input and output per call:

- Request record: `call_id`, `started_at`, `finished_at`, `wrapper_latency_ms`, model, typed question, exact instruction, candidate criteria, and the complete state payload.
- Normalized response: `choice`, `confidence`, `probabilities`, `model`, `input_tokens`, `output_tokens`, `cost`, `latency_ms`, `error`, and `raw_response` when present.
- Valid responses in the verified run contain a probability map whose values sum to approximately `1.0`. Invalid maps remain visible only as raw rejected output with the validation error; they are not rendered as a valid distribution.

Adapter and run evidence:

- `validation`: chosen ID, fallback reason, fallback flag, legal-candidate count, submitted order, and recorded decision/validation latency.
- `submitted_order`: chosen ID, fallback flag, and exact `/choose ...` message.
- Event records: `EVALUATION_SETUP`, `BATTLE_START`, `TURN_DECISION`, and `BATTLE_END`.
- Run summary: 3 requested/completed battles, 77 calls/decisions, 57 choices, 20 fallbacks, 19 provider errors (14 HTTP 503 and 5 timeouts), 1 protocol validation error, 0 illegal actions, 0 stale responses, 0 timer failures, P50/P95/P99 latency, and record-completeness flags.
- Run configuration/status: `gen9randombattle`, Jev model `jev-1.13-free`, 10-second request timeout, one provider request per decision with no retry, run start/finish timestamps, evaluation status, and the configured endpoint in technical metadata.
- Artifact integrity: 77 request/response records and 84 event records are complete; credential redaction scan reports 0 leaks. Render these as technical integrity badges, not as gameplay performance metrics.
- Showdown logs additionally provide battle tags, request messages, turns, switches, faints, and winner lines for the recorded battles. Those events remain owned by the official battle/log surface, with only selected evidence summarized outside it.

Keep the provenance boundary visible: a full Showdown `|request|` payload found in a battle log is `SHOWDOWN RAW INPUT`; the reduced `snapshot` forwarded in `jev_request.state` is `HARNESS → JEV INPUT`. Do not imply that stats, abilities, items, or other raw protocol fields were sent to Jev unless they are actually present in that state payload.

The following are intentionally not presented as if they exist in the current artifacts:

- Separate extraction, calculation, validation, and order-submission durations. Only the recorded response, wrapper, and decision/validation latency values are shown.
- A provider display name. Only the Jev model is in each response; the configured endpoint is run metadata.
- A payload-size field. It may be shown only as a clearly labeled locally derived measurement.
- A Jev raw-websocket frame stream or replay artifact. The latest manifest has no Jev `protocol-replay.json`; show the captured request/order JSON and `Raw protocol frame not captured`.
- Per-battle duration. Current battle-end events provide winner, `won`, and `total_turns`, but not start/end timestamps for each battle.
- A probability value for fallback/error records. Empty probabilities and zero token counts on an error are not successful zero-valued Jev output.
- A strategic score, win chance, damage percentage, KO result, or rationale when the recorded field is an estimate, unknown, or absent.

## 19. Prototype acceptance checklist

The low-fidelity prototype is successful when a viewer can answer the following without opening raw JSON:

- What battle is currently running?
- What did Showdown provide?
- What did the harness calculate?
- What legal candidates were produced?
- What request was sent to Jev?
- What did Jev actually return?
- Was confidence or a probability distribution returned?
- Did validation pass?
- What exact order was submitted?
- Has Showdown observed the result yet?
- Was a fallback used?
- How long did the decision take?

A technical viewer should additionally be able to inspect:

- State snapshot.
- Calculated candidate data.
- Jev request.
- Jev response.
- Validation result.
- Submitted order.
- Relevant captured protocol frames, or an explicit `Raw protocol frame not captured` state when that artifact is unavailable.
- Observed result.
- Redaction status.

The dashboard should communicate the complete observable system without duplicating the battle, fabricating Jev reasoning, or turning the page into an unreadable telemetry console.
