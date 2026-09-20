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
