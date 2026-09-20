# Dashboard Overhaul Design

Status: design basis for implementation

Date: 2026-09-20

## Goal

Replace the accumulated widget-grid dashboard with a polished, battle-first
local showcase that makes the real Pokémon Showdown scene, harness preparation,
and Jev decision output understandable to technical and non-technical viewers
at a normal desktop recording viewport.

The redesign is a presentation overhaul. It does not change the Jev provider,
battle strategy, Showdown connection, or deterministic validation behavior
unless browser validation identifies a small missing status signal.

## Design principles

1. The official Showdown renderer is the single visual source of truth for the
   game.
2. The custom dashboard explains the harness and Jev; it does not redraw the
   game.
3. Real event data drives every visible state. No invented metrics or fake
   reasoning is added for visual effect.
4. The first desktop viewport communicates the battle and current decision
   without scrolling.
5. Technical inspection is available in one click but hidden by default.
6. The layout uses authentic retro battle language without turning into a
   generic neon analytics console.

The binding details are maintained in
[`dashboard-redesign-guardrails.md`](../../design/dashboard-redesign-guardrails.md).

## Audience and story

The dashboard must communicate this sequence visually:

```text
Game State → Harness → Extract / Calculate → Jev Input
Jev Input → Jev Decision → Game Action → Showdown Result
```

The showcase is not meant to expose every internal variable. The default view
selects the small set of facts that demonstrates what the system does. The
full state, request, response, validation record, and protocol frames remain
available through Technical Inspection.

## Layout

At a normal desktop landscape viewport such as 1440×900 or 1600×900:

```text
┌──────────────────────────────────────────────────────────────────────┐
│ brand · turn · backend · showdown · jev · start/status               │
├───────────────────────────────────────────────┬──────────────────────┤
│                                               │ JEV INPUT            │
│                                               │ compact harness      │
│       official Showdown battle bay            │ summary, facts,      │
│       exact 16:9, 640×360 composition         │ legal actions         │
│       scene, HUD, effects, message caption     ├──────────────────────┤
│                                               │ JEV DECISION         │
│                                               │ choice, confidence,  │
│                                               │ real probabilities,  │
│                                               │ latency/fallback     │
├───────────────────────────────────────────────┴──────────────────────┤
│ VALIDATE → ACT → OBSERVED RESULT                 TECHNICAL INSPECT   │
└──────────────────────────────────────────────────────────────────────┘
```

The battle bay occupies roughly 70% of the main width and the decision rail
roughly 30%. The right rail matches the battle bay height. The battle bay is
not placed in a 640×380 wrapper, and it does not have a separate log/status
block below it. The latest battle message is a compact overlay or caption
inside the bay.

The official scene keeps its internal breathing room because that is part of
the real Showdown composition. The dashboard removes only avoidable outer
space created by the host layout.

## Game/battle ownership

The official renderer owns:

- arena/background and perspective platforms;
- active Pokémon sprites and animation;
- HP, levels, types, statuses, and team Poké Ball indicators;
- opponent fog of war and revealed team state;
- terrain, weather, hazards, and move effects;
- battle message text and observed outcomes.

The dashboard must not add duplicate active-Pokémon cards, team rows, terrain
cards, weather cards, HP bars, or battle history. The existing custom telemetry
arena remains available only when the official renderer is unavailable, with
explicit renderer-fallback attribution.

## Jev Input presentation

Use one compact card labelled `JEV INPUT` with a small attribution such as
`HARNESS-SERIALIZED STATE`. Do not split it into separate `GAME STATE` and
`JEV INPUT` views.

Show only the decision-relevant summary:

- turn and active matchup names, without duplicate sprites or HP bars;
- legal action count and a readable top-K list of actions;
- a short field/context line only when that field is part of Jev's serialized
  state;
- deterministic fact chips from the current candidate facts, such as type
  multiplier, estimated damage range, KO status, priority, speed relation, or
  switch cost.

Facts are harness-owned and must be visually distinguished from Jev output.
Unavailable facts are omitted rather than guessed.

## Jev Output presentation

Use one compact card labelled `JEV DECISION`. During the API call, only this
card should visibly wait or pulse.

Show actual fields returned by Jev or measured by the adapter:

- selected typed choice;
- confidence;
- probability distribution across legal actions;
- configured model identifier, such as `jev-1.13-free`;
- inference latency;
- usage/cost when available;
- fallback/error state.

Do not manufacture chain-of-thought, win chance, damage confidence, risk
score, psychological explanation, or an invented model version. The selected
choice and distribution should animate when the real response arrives.

## Action trace and temporal truth

The bottom trace is compact and chronological:

```text
VALIDATE → ACT → OBSERVED RESULT
```

- `VALIDATE` shows that the selected choice is legal and whether fallback was
  required.
- `ACT` shows the exact submitted Showdown order and its submission state.
- `OBSERVED RESULT` stays `AWAITING SHOWDOWN` until the protocol reports the
  result, then shows the actual observed event/result.

A previous battle event must not be presented as the result of the current
order. The official message caption may show the latest protocol event, while
the trace clearly distinguishes pending and resolved phases.

## Header and system status

Use a compact header with purposeful information only:

- project/agent identity;
- current turn or battle state;
- backend/WebSocket status;
- Showdown battle/search status;
- Jev availability/model/fallback status;
- `START JEV BATTLE` while idle, and a truthful non-action state such as
  `JEV PLAYING` while active.

Remove slogans, `OBSERVABLE DATA`, duplicate latency/cost badges, and text that
merely repeats the visual. Errors and degraded states must be short,
understandable, and visible without dominating the battle.

## Technical Inspection

Provide one single-click `TECHNICAL INSPECT` control. It opens a drawer or
secondary surface, not a normal always-visible panel. It can contain tabs or
sections for:

- harness snapshot/state;
- Jev request, question, and criteria;
- Jev response and raw probabilities;
- validation/fallback/submitted order;
- recent Showdown protocol frames.

This surface may scroll independently. The main dashboard remains clean.

## Outcomes and errors

Do not use a large modal overlay for victory, defeat, or normal battle end.
Reuse the official final scene, message caption, status rail, and action trace.
Preserve the final official scene after `BATTLE_END`.

If Jev fails, show `FALLBACK USED` with the adapter reason and fallback action;
do not label the fallback as a Jev decision. If the official renderer fails,
hide it and show the existing telemetry fallback with explicit attribution.

## Assets and visual language

Battle visuals come from the audited official Showdown bundle and its hosted
official assets. Image generation must not be used to recreate Pokémon,
Showdown battle stages, move effects, HP/team UI, or battle animations.

The outer shell may use code-native CSS for pixel borders, scanlines, spacing,
and arcade framing. Only if a new non-Pokémon bitmap asset is genuinely
needed should it be generated with imagegen and committed as a dashboard
chrome asset. No bitmap is required by this design by default.

## Responsive behavior

Desktop is the primary target. At smaller widths, collapse the decision rail
below the battle bay and allow the inspector to occupy the full width. Keep
the official 16:9 battle bay readable; do not shrink it into a thumbnail just
to preserve every secondary detail.

## Non-goals

- Rewriting the Pokémon Showdown renderer.
- Building a 3D engine or custom move-effect system.
- Adding a chat, ads, matchmaking UI, or full Showdown website chrome.
- Adding an LLM or simulated reasoning trace.
- Adding a new frontend framework or build pipeline for this overhaul.
- Changing battle strategy, Jev request semantics, or fallback selection.

## Acceptance criteria

The redesign is complete when:

- the official battle scene is the dominant visual at 1440×900 or 1600×900;
- the stage uses the exact 640×360 composition scaled into a 16:9 bay;
- no avoidable blank wrapper space or separate log/status block appears below
  the stage;
- no duplicate game-state widgets exist outside the official renderer;
- Jev Input clearly shows harness-serialized context, legal actions, and
  selected deterministic facts;
- Jev Output shows only actual Jev/adapter fields and real probabilities;
- the action trace is chronological and truthful before and after resolution;
- the Technical Inspection path exposes full diagnostic data without cluttering
  the default view;
- backend, Showdown, Jev, fallback, and current game states are visible and
  understandable;
- normal outcomes do not create modal overlays;
- healthy live battles continue rendering official protocol-driven effects;
- the existing test suite passes;
- Playwright browser validation at a standard desktop viewport shows no
  meaningful console, network, or WebSocket errors and the screenshot is
  visually demo-ready.
