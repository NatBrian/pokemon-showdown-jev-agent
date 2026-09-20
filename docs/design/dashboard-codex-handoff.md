# Codex Handoff: Rewrite the Dashboard From Scratch

Copy the prompt below into a new Codex session started in this repository.

---

## Task

You are taking over:

```text
C:\Users\Admin\Documents\Github\autonomous-pokemon-showdown-jev-agent
```

You have no previous conversation context. You are responsible for replacing
the dashboard with a genuinely new, polished, demo-ready UI for this project.

Do not patch or cosmetically refine the previous dashboard. It was deleted
because its visual structure remained too similar to an earlier low-quality
dashboard. Build the custom dashboard layer from scratch using the canonical
specification below.

Use native execution. Do not use subagents unless explicitly requested. Use
Superpowers skills where applicable. Plan first, create a task list, inspect
the repository, then implement and verify the result.

## Read these documents first

Read this document first:

```text
docs/design/dashboard-canonical-spec.md
```

Then read the technical context:

```text
docs/research/phase-0-jev-opencode.md
docs/research/phase-1-research-and-architecture.md
docs/design/showdown-battle-ui-direction.md
```

The canonical specification is authoritative for all dashboard decisions. If
an older design document conflicts with it, follow the canonical
specification.

## Current repository state

The legacy custom dashboard was intentionally deleted. These files are gone:

```text
src/jev_showdown/web/static/index.html
src/jev_showdown/web/static/style.css
src/jev_showdown/web/static/app.js
tests/unit/test_frontend_assets.py
```

The deletion is intentional. Do not restore the old dashboard from Git
history.

Preserve and understand these working systems:

```text
src/jev_showdown/                         Python backend and Pokémon harness
src/jev_showdown/web/server.py             Web server and WebSocket bridge
src/jev_showdown/web/static/showdown-renderer.js
                                            Official Showdown renderer adapter
src/jev_showdown/web/static/showdown/      Official Showdown renderer/assets
```

Do not rewrite the official `showdown/` renderer bundle. Do not replace it
with a hand-built Pokémon scene. Only modify `showdown-renderer.js` if the
adapter genuinely needs a small integration change.

## Core product goal

The browser dashboard is a transparent showcase of Jev making real decisions
in a real Pokémon Showdown Generation 9 Random Battle through the actual Jev
OpenCode route.

The viewer must understand:

```text
Showdown game state
        -> harness extracts and calculates
        -> Jev Input
        -> Jev typed decision
        -> validation and Showdown order
        -> Showdown displays the observed result
```

The audience includes both technical and non-technical viewers. The UI must
be visually engaging when recorded for LinkedIn, but technically truthful.

## Non-negotiable visual ownership rule

The official Pokémon Showdown renderer is already the complete live game UI.
Preserve it as the source of truth and show it prominently.

It already provides:

- battle arena, platforms, terrain, and weather;
- active Pokémon and trainers;
- animated sprites and movement;
- HP bars, levels, types, statuses, and stat changes;
- both sides' Poké Ball/team indicators;
- opponent fog of war;
- battle messages and the battle log;
- move effects, switch effects, faint effects, hazards, and Tera effects;
- battle outcomes and final battle scene.

Do not recreate any of those elements in custom HTML/CSS. Do not add custom
team panels, opponent panels, active-Pokémon cards, HP bars, terrain cards,
weather cards, battle-message cards, battle-log cards, damage-result cards,
or Pokémon battle-history panels.

The screenshot in the prior discussion showed the exact kind of official scene
that must be preserved: the arena, Pokémon, trainers, Poké Balls, HP/status
UI, and message box all remain Showdown-owned.

The custom dashboard is a Jev observability console attached to the official
game window. It is not a second Pokémon game client.

## Required custom dashboard content

### 1. Jev Input

Show a concise live summary of what the harness sends to Jev:

- current turn;
- active matchup names as text only, without duplicate sprites or HP bars;
- public state facts serialized into the Jev request;
- legal-action count and top-K legal action labels;
- deterministic facts actually available for the current snapshot, such as
  type effectiveness, damage range, speed/priority, KO estimate, or switch
  cost;
- concise question/criteria context when useful.

If a fact is unavailable, omit it. Never invent values merely to fill the UI.

### 2. Jev Decision

Show only actual Jev or adapter evidence:

- real loading state while Jev is evaluating;
- selected typed action;
- confidence;
- probability distribution over legal actions;
- configured model identifier;
- measured inference latency;
- usage and cost when available;
- explicit fallback/error attribution.

Do not manufacture chain-of-thought, natural-language reasoning, win chance,
risk score, damage score, psychological explanation, or an invented model
version. Jev is a typed decision engine, not a chat model.

### 3. Compact adapter status

Show the fast adapter sequence inside the Jev console:

```text
LEGAL -> ORDER SUBMITTED -> AWAITING SHOWDOWN
```

This means:

- `LEGAL`: Jev's choice was checked against current legal actions;
- `ORDER SUBMITTED`: the exact Showdown order was sent;
- `AWAITING SHOWDOWN`: Showdown has not reported the result yet.

The official Showdown scene is the only place that displays the real message,
damage, animation, faint, win, loss, or tie. A small `RESULT OBSERVED` status
is allowed after the protocol reports it, but do not duplicate the result text.

### 4. Jev decision history

History means recent Jev outputs, not Pokémon battle history.

Show the five most recent decisions by default, for example:

```text
T12  POWER GEM      96%  842 ms  ACCEPTED
T11  SWITCH GASTRO  71%  604 ms  ACCEPTED
T10  PROTECT        83%  517 ms  ACCEPTED
```

The list resets when a new battle starts and remains visible after a battle
ends until the next battle begins. It must never copy Showdown's battle log.

### 5. Technical Inspection

Provide one clear click target that opens a secondary drawer or view. It is
hidden by default and must not make the main screen look like a developer
console.

It may expose formatted or raw:

- harness state and deterministic calculations;
- Jev state, questions, and criteria;
- exact Jev request and response;
- validation/fallback result;
- submitted Showdown order;
- selected Jev history entry;
- recent Showdown protocol frames.

## Design direction

The rewrite must not be another generic dark dashboard made of many bordered
cards. The previous structure is explicitly rejected.

Design the official Showdown scene as the finished game window and the custom
UI as one focused Jev command/observability console beside it. Make the
current Jev decision the visual focus of the custom console; keep history and
inspection secondary.

Use a coherent retro-arcade language around the scene: readable pixel-style
type, restrained arcade framing, purposeful status colors, strong spacing,
and a clear focal hierarchy. Do not cover the official battle scene with
dense technical overlays. Do not add generated Pokémon art or generated
replacement battle effects.

Avoid:

- generic three-column analytics layouts;
- duplicated `LIVE BATTLE` labels;
- duplicate terrain/weather/team sections;
- a large static vertical pipeline diagram;
- a large bottom `VALIDATE / ACT / RESULT` card strip;
- decorative slogans and marketing claims;
- paragraphs explaining what the visualization already communicates.

The only normal visible loading state should be Jev API evaluation. Harness
extraction, calculation, validation, and order submission should appear as
short state changes or compact badges.

## Runtime requirements

- Use the repository `.venv` interpreter.
- Use the actual Jev/OpenCode integration documented in
  `docs/research/phase-0-jev-opencode.md`.
- Do not introduce a mock Jev provider or simulated battle flow.
- Use the configured `.env` Showdown account.
- Use real public Pokémon Showdown Gen 9 Random Battles.
- Keep viewer controls simple: start the battle and inspect technical data.
- Do not add manual move selection, settings screens, replay systems, or
  built-in video recording.

## Implementation scope

Create a new implementation for the missing custom dashboard files:

```text
src/jev_showdown/web/static/index.html
src/jev_showdown/web/static/style.css
src/jev_showdown/web/static/app.js
```

Write new dashboard tests appropriate to the new design and actual event
contracts. Do not recreate the deleted tests by restoring their old selectors.

Before coding:

1. Inspect the backend WebSocket/event contracts.
2. Inspect `showdown-renderer.js` and the official renderer integration.
3. Create a written implementation plan and task list.
4. Confirm the new UI has a clear ownership boundary between Showdown and the
   Jev console.

## Validation requirements

Do not claim success from code inspection alone.

Use Playwright at a normal desktop viewport such as 1440x900 or 1600x900.
Actually inspect screenshots with vision. The human viewer will see the
browser, not the source code.

Validate:

- idle state and start flow;
- real backend/WebSocket connection;
- real Jev/OpenCode decision loading and response;
- real Showdown battle scene with sprites, arena, messages, and effects;
- Jev Input values matching the actual request;
- Jev Decision values matching the actual response;
- Jev decision history appending real decisions;
- validation/order status transitions;
- explicit fallback behavior;
- Technical Inspection opening and showing real data;
- battle-end scene preserved without a modal;
- no duplicate battle UI outside Showdown;
- no horizontal overflow or excessive scrolling;
- no browser console errors or missing required assets.

Run the full relevant test suite and a real battle before declaring completion.
Document the visual and runtime evidence in a validation markdown file.

## Final delivery

Before finishing:

- review the screenshot as a human viewer;
- compare it against `dashboard-canonical-spec.md` line by line;
- remove anything that duplicates Showdown or invents Jev behavior;
- ensure the repository is clean and changes are committed;
- report exact test results, browser validation results, and real battle
  evidence.

Do not stop at “the page loads.” The result must be a genuinely new,
understandable, visually coherent, technically truthful dashboard suitable for
recording.

---
