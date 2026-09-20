# Dashboard Redesign Guardrails

Status: binding implementation guidance

Date: 2026-09-20

## Purpose

The generated dashboard image is a visual composition reference only. It is
not an accurate representation of production assets, live telemetry values,
Jev output, or the official Pokémon Showdown scene.

Generated artwork may suggest layout, spacing, color, and hierarchy. The
implemented dashboard must use the real Showdown renderer and actual backend
event payloads.

## Single source of truth

The official Showdown renderer owns the complete visual game state:

- battle arena and perspective platforms;
- active Pokémon sprites;
- HP, levels, types, and status;
- revealed team indicators and opponent fog of war;
- weather, terrain, hazards, and field effects;
- move animations, switch/faint effects, and battle messages;
- the final battle outcome.

Do not create second custom versions of these elements in the dashboard shell.
In particular, do not add separate active-Pokémon cards, team-list panels,
terrain panels, weather panels, duplicate HP bars, or duplicate battle history
outside the official scene.

The fallback arena remains an error path only. It must not compete with the
official renderer during a healthy battle.

## Dashboard composition

The normal desktop view is a tightly fitted two-region layout:

- approximately 70%: one exact 16:9 official Showdown battle bay;
- approximately 30%: one compact Jev decision rail;
- bottom: a thin chronological action trace.

The official battle scene must not be placed inside a tall generic card with
avoidable blank space. The external battle log/status treatment should be
compact and integrated into or immediately adjacent to the battle bay.

The right rail contains only two primary concepts:

1. `JEV INPUT` — the harness-serialized decision context;
2. `JEV DECISION` — the actual Jev response.

`GAME STATE` must not become a second tab or second full representation of the
same battle state. If a field is already visible in the official renderer, the
Jev Input panel may reference it compactly but must not redraw it.

## Jev Input rules

Jev Input is a transparency summary, not another Pokémon battle HUD. It may
show:

- turn and active matchup names, without duplicate sprites or HP bars;
- legal-action count and concise action labels;
- a short field/context line when that field is actually serialized to Jev;
- deterministic fact chips such as type multiplier, damage range, KO estimate,
  speed relation, priority, or switch cost.

These values must come from the current snapshot and candidate facts. If a
fact is unavailable, omit it instead of inventing a value.

## Jev Output rules

Jev Output may show only fields actually returned by Jev or measured by the
adapter:

- selected choice;
- confidence;
- probability distribution over legal actions;
- model identifier;
- inference latency;
- usage/cost when available;
- fallback/error state.

Do not display generated win chances, damage scores, risk scores, invented
model versions, psychological explanations, or chain-of-thought. Jev is a
typed decision system; show its real decision evidence directly.

The probability visualization must represent Jev's actual action
distribution, for example:

```text
Earthquake       62%
Rapid Spin       18%
Close Combat     13%
Knock Off          7%
```

## Truthful action timeline

The bottom trace is chronological:

```text
VALIDATE  →  ACT  →  OBSERVED RESULT
```

- `VALIDATE` means the selected Jev choice was checked against legal actions.
- `ACT` means the exact Showdown order was submitted.
- `OBSERVED RESULT` is populated only after Showdown reports the result.

Before the protocol resolves the order, the result must say `AWAITING
SHOWDOWN` or equivalent. It must not show predicted damage or an unrelated
previous event as the result of the current action. Previous events belong in
the official battle message or Technical Inspection and should be labelled as
such.

## Status and copy rules

The header should expose compact real status indicators for:

- backend connection;
- Showdown/battle connection;
- Jev availability or fallback;
- current game state.

Use `START JEV BATTLE` only while idle. During a live battle, use a truthful
non-action state such as `JEV PLAYING`.

Avoid decorative slogans, marketing copy, and redundant labels such as:

- `OBSERVABLE DATA` when the dashboard already visibly exposes telemetry;
- `SAME GAME. DEEPER INSIGHT.`;
- `PLAY. ANALYZE. IMPROVE. REPEAT.`;
- `Pokémon Showdown Rating Battles` when the actual format is Gen 9 Random
  Battles.

## Technical Inspection

Provide one single-click Technical Inspection path for technical viewers. It
may expose formatted or raw:

- harness state;
- Jev questions and criteria;
- Jev response;
- validation/fallback result;
- recent Showdown protocol frames.

The inspector is hidden by default. It must not turn the main demo view into a
developer console.

## Mockup interpretation checklist

The earlier generated mockup contains illustrative mistakes and must not be
copied literally:

- its duplicated active-matchup cards must be removed;
- its `GAME STATE` / `JEV INPUT` split must become one Jev Input summary;
- its `Win chance`, `Damage`, and `Risk` bars must be removed unless the
  backend later produces those exact metrics;
- its `MODEL v3.1` must be replaced by the configured real model identifier;
- its selected action and observed event must be temporally consistent;
- its generated battle art must be replaced by the official Showdown
  renderer;
- its decorative slogans and invented battle labels must be removed.

The image remains useful for the overall composition: a large battle-first
viewport, a compact Jev rail, and a thin action trace.

## Product objective and audience

This is a local, recording-ready showcase for technical and non-technical
viewers. A viewer should understand the system without reading source code:

```text
Game State → Harness → Extract / Calculate → Jev Input
Jev Input → Jev Decision → Game Action
```

The dashboard is not a generic analytics console and is not a written essay.
The battle, decision state, and observed result should carry the explanation.

## Real-time presentation

The interface should feel alive through real state changes, not simulated
reasoning:

- the official scene updates from the raw Showdown protocol stream;
- only the Jev decision area visibly waits during API inference;
- input, validation, and order submission use short state transitions because
  those operations are normally near-instant;
- the selected action receives a clear active state while it is validated and
  submitted;
- the official battle message/effect shows what Showdown actually observed;
- confidence/probability bars animate only when a real Jev response arrives;
- no chain-of-thought, psychological explanation, or fake multi-step reasoning
  is shown.

The event sequence must remain truthful when a battle is fast, a renderer is
still mounting, a WebSocket reconnects, or a battle ends between two UI
updates.

## Information density and responsive behavior

The primary recording target is a normal desktop/laptop landscape viewport,
with browser validation at a standard size such as 1440×900 or 1600×900. The
first viewport must show the battle bay, Jev decision summary, system status,
and action trace without page scrolling.

Use top-K summaries for data that cannot fit:

- show the selected action plus the most useful legal alternatives in the
  decision rail;
- show a small number of deterministic fact chips;
- keep full state, criteria, response, validation, and protocol frames in the
  single-click inspector;
- allow the inspector or protocol history to scroll independently.

Mobile support may collapse the rail below the battle bay, but it must not
drive the desktop composition or shrink the official scene into an unreadable
thumbnail.

## Asset ownership

Production battle visuals must use the audited official Showdown renderer,
sprites, arena backgrounds, effects, and protocol mapping. Do not use image
generation to recreate or replace Pokémon, battle stages, move effects, HP
bars, team indicators, or animations.

Custom dashboard chrome may use CSS and existing code-native UI primitives.
If a new non-Pokémon bitmap asset is genuinely needed for the outer arcade
frame, CRT texture, or decorative background, generate it with the image
generation tool, store it in the repository, and test it at the recording
viewport. Do not add generated art merely to fill space.

## System status and degraded states

The compact status rail must expose, without dominating the battle:

- backend/WebSocket connection;
- Showdown battle connection or search state;
- Jev availability and active model when known;
- current game state such as idle, connecting, waiting for decision, playing,
  reconnecting, ended, or fallback.

If Jev fails, the dashboard must say that the adapter used a deterministic
fallback and identify the fallback action. It must never present the fallback
as a Jev decision. If the official renderer fails, show the existing
telemetry fallback with explicit renderer attribution.

## Outcomes and notifications

Winning, losing, and battle-ended states must reuse the battle bay, message
caption, status rail, and action trace. Do not show a large popup or modal for
normal outcomes. Preserve the final official scene and label the observed
result in place.

## Visual QA acceptance

Before implementation is considered complete, validate the actual browser
experience at a standard landscape viewport with Playwright and inspect the
rendered screenshot visually. Check:

- the official battle bay is the dominant, tightly fitted 16:9 region;
- there is no avoidable blank wrapper space or separate log/status block below
  the stage;
- no duplicate Pokémon, team, terrain, weather, or HP widgets appear outside
  the official scene;
- the right rail remains readable without hunting or excessive scrolling;
- the Jev decision uses actual response fields;
- the action trace is chronological and truthful;
- normal outcomes do not create modal overlays;
- healthy, fallback, reconnecting, and ended states are understandable;
- browser console errors, failed required asset requests, and WebSocket errors
  are absent or explicitly handled.
