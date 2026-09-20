# Dashboard Canonical Specification

Status: BINDING DESIGN SPECIFICATION
Date: 2026-09-20

This document is the current source of truth for the dashboard rewrite. Older
mockup-oriented documents may contain historical ideas, but they must not
override this specification.

## Product purpose

The dashboard is a local, recording-ready showcase of Jev making decisions in
a real Pokemon Showdown Gen 9 Random Battle. It must be understandable to
technical and non-technical viewers without becoming a generic analytics
dashboard or a second Pokemon game client.

The viewer should understand this flow:

```text
Showdown game state
        -> harness extracts and calculates
        -> Jev Input
        -> Jev typed decision
        -> validation and Showdown order
        -> Showdown displays the observed result
```

## Non-negotiable ownership boundary

The official Pokemon Showdown renderer owns the complete live game window.
Preserve its rendered content as-is, including:

- arena, platforms, terrain, and weather;
- active Pokemon, trainers, sprites, and animations;
- HP bars, levels, statuses, stat changes, and type indicators;
- both sides' Poké Ball/team indicators and opponent fog of war;
- battle messages and the battle log;
- move effects, switch effects, faint effects, hazards, and Tera effects;
- battle outcomes and the final battle scene.

Do not recreate any of these elements in the custom dashboard. Do not add
custom active-Pokemon cards, team rows, terrain cards, weather cards, HP bars,
battle-message panels, battle-log panels, damage-result panels, or Pokemon
battle-history panels.

The agent controls one side of the match. The opponent and both teams are
already represented by the official Showdown scene; they are not custom
dashboard data visualizations.

The dashboard must not use an iframe or the full Showdown website. The existing
official renderer adapter and its local/remote assets remain the implementation
boundary for the game view.

## Desktop composition

Use a normal landscape recording viewport such as 1440x900 or 1600x900.
Important information must be visible without page scrolling.

The composition consists of:

1. One dominant official Showdown battle window, kept at the exact 16:9 scene
   ratio and scaled without cropping important content.
2. One custom Jev observability console beside the scene.
3. A minimal header/status area for start and connection state.

The official scene must not sit inside a tall generic card with avoidable blank
space. Do not place a separate log or battle-status block underneath it.

The visual language around the scene may use restrained retro-arcade styling:
pixel-readable typography, purposeful arcade borders, dark indigo/navy
surfaces, and small status accents. Do not cover the Pokemon scene with dense
neon telemetry or decorative generated art.

## Jev observability console

The console is the only custom information surface that needs to be prominent.
It must feel like one focused decision instrument, not a collection of generic
cards.

### Jev Input

Show a concise, live summary of what the harness sends to Jev:

- turn number and active matchup names;
- the public state facts serialized into the request;
- legal-action count and top-K legal action labels;
- deterministic calculations actually available for the current snapshot, such
  as type effectiveness, damage range, speed/priority, KO estimate, or switch
  cost;
- concise question and criteria context when it helps the viewer understand
  the request.

Do not redraw sprites, HP bars, team rows, weather, terrain, or the battle log.
If a fact is unavailable, omit it. Never invent a value for visual effect.

### Jev Decision

Show only actual Jev or adapter evidence:

- loading state while the Jev API is evaluating;
- selected typed action;
- confidence;
- probability distribution over legal actions;
- configured model identifier;
- measured inference latency;
- usage and cost when available;
- explicit fallback/error attribution.

Do not manufacture chain-of-thought, natural-language reasoning, win chance,
risk score, damage score, psychology, or an invented model version.

### Adapter status

Validation and action are compact status transitions in the console:

```text
LEGAL -> ORDER SUBMITTED -> AWAITING SHOWDOWN
```

- `LEGAL`: the Jev choice was checked against the current legal actions.
- `ORDER SUBMITTED`: the exact Showdown order was sent.
- `AWAITING SHOWDOWN`: the protocol has not reported the result yet.

The official Showdown scene is the only place that shows the actual battle
message, damage, effect, faint, win, loss, or tie. The custom console may show
`RESULT OBSERVED` as a small adapter state after Showdown reports it, but must
not duplicate the event or result text.

### Jev decision history

History means recent Jev outputs, not Pokemon battle history. Show a compact,
scrollable top-K list of decisions such as:

```text
T12  POWER GEM      96%  842 ms  ACCEPTED
T11  SWITCH GASTRO  71%  604 ms  ACCEPTED
T10  PROTECT        83%  517 ms  ACCEPTED
```

Each row may expose turn, selected action, confidence, latency, and validation
status. Selecting a row may populate Technical Inspection with the full
request, response, and validation data. Do not copy the official Showdown
 battle log into this list.

The default visible history is the five most recent Jev decisions. It resets
when a new battle starts and remains visible after a battle ends until the
next battle begins.

## Technical Inspection

Provide one clear click target that opens a secondary drawer or view. It is
hidden by default and must not make the main dashboard look like a developer
console.

It may expose formatted or raw:

- harness state and deterministic calculations;
- Jev state, questions, and criteria;
- exact Jev request and response;
- validation/fallback result;
- submitted Showdown order;
- selected Jev decision-history entry;
- recent Showdown protocol frames for debugging.

## Real-time behavior

The interface must show actual state changes, not simulated reasoning:

- the official battle scene updates from the Showdown protocol stream;
- the Jev area is the only area that normally waits during API inference;
- extraction, calculation, validation, and submission use short transitions;
- confidence/probability visuals animate only after a real Jev response;
- a Jev history row is appended only after a real Jev response;
- the official Showdown message/effect is the observed result;
- no hidden reasoning is displayed.

## Startup, status, and degraded states

The single start action is application orchestration, not a native Showdown GUI
button. The visible startup sequence may be:

```text
READY -> CONNECTING -> AUTHENTICATING -> SEARCHING -> MATCH FOUND
      -> INITIALIZING -> JEV PLAYING
```

Show compact indicators for backend, Showdown, Jev, and game state. If Jev
fails, state clearly that a deterministic fallback was used and identify the
fallback action. Never present fallback output as a Jev decision. If the
official renderer fails, identify the renderer failure and show only the
existing telemetry fallback.

Normal wins, losses, ties, battle messages, and effects must not use a large
modal overlay. Preserve the official final scene.

## Explicitly excluded from the rewrite

- custom Pokemon battle rendering;
- custom battle message or battle log rendering;
- custom team/opponent panels;
- custom terrain/weather/HP panels;
- duplicated battle-result cards;
- duplicated Pokemon battle history;
- fake Jev reasoning or an LLM-style thought stream;
- viewer controls for choosing moves or switches;
- built-in recording or replay-production features;
- decorative marketing claims.

## Acceptance criteria

The rewritten dashboard is acceptable only when:

- a real Showdown battle scene is the dominant visual;
- no custom UI duplicates its game elements;
- the harness input, Jev output, validation, and submitted order are clear;
- Jev decision history is visibly distinct from Showdown battle history;
- loading belongs primarily to real Jev inference;
- fallback is explicit and truthful;
- technical inspection is one click away;
- the first desktop viewport is readable without scrolling;
- a Playwright screenshot has been visually inspected at a normal viewport;
- a real battle has been exercised through the actual Jev/OpenCode path.
