# Dashboard UI Elements

Status: Visual mockup specification only.  
This document does not define application logic, data models, APIs, or implementation details.

Reference image: [dashboard-mockup-final.png](dashboard-mockup-final.png)

The values shown in the mockup are illustrative placeholders. Real Pokémon, moves, HP values, probabilities, latency, damage ranges, and labels may change when connected to live battle data.

## 1. Overall visual direction

The dashboard should feel like a polished arcade Pokémon battle screen with a technical Jev observation layer.

Visual characteristics:

- 1990s arcade and pixel-art inspiration;
- deep indigo/navy background;
- pixel-style headings and labels;
- CRT scanline and glow accents;
- cyan, electric blue, magenta, yellow, green, and red status colors;
- chunky bordered panels;
- clear game-like status indicators;
- modern readability suitable for a recorded LinkedIn showcase.

The dashboard should feel like a game interface first and an engineering visualization second.

## 2. Page shell

### Header

Visible elements:

- Project title: AUTONOMOUS POKÉMON BATTLE AGENT
- Subtitle: GEN 9 RANDOM BATTLES • POWERED BY JEV
- Primary button: START JEV BATTLE
- System status: OBSERVABLE DATA
- Latency badge: LATENCY 184 MS
- Cost badge: COST $0
- Small tagline: SAME GAME. DEEPER INSIGHT.

The values and wording may be adjusted later to match the actual project configuration.

### Main viewport

The mockup is designed as a wide desktop dashboard for screen recording.

Recommended visual proportions:

- left battle region: approximately one third of the width;
- center Jev Input region: approximately one third;
- right Jev Output region: approximately one third;
- bottom action/result strip across the page.

## 3. Left region: Live Battle

Panel title:

LIVE BATTLE

Visible elements:

- turn indicator, such as TURN 12;
- format label, such as Gen 9 Random Battle;
- weather indicator;
- terrain indicator;
- battle arena background;
- player active Pokémon;
- opponent active Pokémon;
- Pokémon name;
- Pokémon level;
- Pokémon type badges;
- HP bar;
- HP percentage or display value;
- status icons;
- player team row;
- opponent team row;
- selected/active Pokémon highlight;
- fainted or unavailable team indicators;
- current battle prompt area.

Example placeholder content:

- GARCHOMP
- HEATRAN
- DRAGON
- GROUND
- FIRE
- STEEL
- HP 357 / 357
- HP 261 / 344
- What will Garchomp do?

The exact sprite, artwork, HP, and team content will come from the real battle later.

### Team rows and information visibility

The live battle area must include two separate six-slot team rows beneath the arena:

- **YOUR TEAM** — show the player's known six Pokémon from the start of the battle. Each slot can show the species/sprite, active highlight, HP/status summary where available, and fainted or unavailable state.
- **OPPONENT TEAM** — show six Poké Ball or unknown placeholders until the opponent's Pokémon are revealed by Showdown. Replace a placeholder with a species/sprite only after that Pokémon has appeared or otherwise been explicitly revealed.

For standard Gen 9 Random Battle, the opponent's complete roster is not available at the beginning because the format does not use Team Preview. The protocol exposes the opponent's team size, but not the identities of unrevealed Pokémon. The visual must therefore never guess or display hidden opponent species, moves, items, abilities, or Tera type.

The unknown slots represent remaining team capacity, not a claim about the opponent's original team order. A revealed Pokémon may be shown by reveal order or by the identity tracked by the battle state.

Team-slot visual states:

| State | Visual treatment |
| --- | --- |
| Unknown opponent slot | Closed Poké Ball, subdued glow, no species label |
| Revealed Pokémon | Sprite/icon, species label, known type badges |
| Active Pokémon | Bright outline or animated selection frame |
| Fainted Pokémon | Grayscale or crossed-out sprite with faint marker |
| Revealed item/ability/status | Small badge only after Showdown explicitly reveals it |

If a future format includes Team Preview, the same row can show the revealed preview roster while still omitting details that Team Preview does not expose. The implementation should detect the actual battle protocol state rather than assuming every format has the same visibility rules.

Protocol references for this visibility behavior:

- [Official Gen 9 Random Battle format definition](https://github.com/smogon/pokemon-showdown/blob/master/config/formats.ts#L26-L32)
- [Pokémon Showdown simulator protocol](https://github.com/smogon/pokemon-showdown/blob/master/sim/SIM-PROTOCOL.md)
- [poke-env Battle documentation](https://poke-env.readthedocs.io/en/stable/modules/battle.html)

## 4. Turn History

Location: lower portion of the Live Battle panel.

Panel title:

TURN HISTORY

Visible elements:

- compact event cards;
- turn number;
- actor;
- move or action;
- damage indicator;
- status indicator;
- switch indicator;
- faint indicator;
- expand control.

Example placeholder cards:

- TURN 9 — Opponent used Scald
- TURN 10 — Garchomp used Swords Dance
- TURN 11 — Opponent used Magma Storm

Example event badges:

- -28%
- BURN
- DEF +2
- TRAPPED

History should remain compact so the battle view stays dominant.

## 5. Center region: Jev Input

Panel title:

JEV INPUT

Source label:

CALCULATED BY HARNESS

This panel represents the information prepared for Jev. It is a visual representation of the input, not a raw JSON dump.

### Battle State card

Visible elements:

- current active Pokémon;
- opponent active Pokémon;
- HP values;
- status values;
- type badges;
- turn number;
- known battle context.

Section label:

BATTLE STATE (SHOWDOWN)

### Field Conditions card

Visible elements:

- small field image or visual field indicator;
- weather;
- terrain;
- side condition indicators where useful.

Section label:

FIELD CONDITIONS

### Calculated Facts card

Visible elements:

- type effectiveness;
- estimated damage range;
- KO status;
- priority;
- other concise deterministic facts.

Section label:

CALCULATED FACTS

Example placeholder badges:

- GROUND 2×
- DAMAGE 72–85%
- KO NOT GUARANTEED
- PRIORITY 0

### Legal Actions card

Visible elements:

- candidate action name;
- move or switch type;
- short action description;
- selected/highlighted candidate;
- available action count.

Section label:

LEGAL ACTIONS (3)

Example placeholder actions:

- MOVE_EARTHQUAKE
- MOVE_OUTRAGE
- MOVE_SWORDS_DANCE

The action names are visual examples and may change with each battle.

## 6. Right region: Jev Output

Panel title:

JEV OUTPUT

Status label:

API INFERENCE (MODEL)

This region is the main visual focus for Jev's response time.

### Processing state

Visible elements:

- JEV PROCESSING...;
- arcade-style loading indicator;
- request status checklist;
- inference latency;
- response status;
- completed indicator.

Example status labels:

- Input received
- Calling model API...
- Waiting for response...
- Response received
- Parsing decision
- API INFERENCE 184 MS

If the provider fails and the adapter must keep the battle alive, show a prominent status message such as:

- JEV FAILED — FALLBACK USED
- FALLBACK ACTION: MOVE_EARTHQUAKE

The fallback must be visually attributed to the adapter, never displayed as a Jev output.

Only this region should appear to wait meaningfully during a decision. The harness, validation, and action panels should visually communicate near-instant completion.

### Decision card

Section label:

DECISION (JEV OUTPUT)

Visible elements:

- typed choice;
- selected action icon;
- action type badge;
- confidence percentage;
- completed status.

Example placeholder content:

- CHOICE
- MOVE_EARTHQUAKE
- GROUND
- CONFIDENCE 91%
- COMPLETED

### Probability card

Section label:

PROBABILITIES (JEV OUTPUT)

Visible elements:

- all candidate actions;
- probability percentage;
- horizontal probability bars;
- candidate type badge;
- selected candidate highlight.

The probability chart should make Jev's distribution immediately understandable without requiring a JSON viewer.

## 7. Inspect Data

Location: lower portion of the Jev Output panel.

Panel title:

INSPECT DATA

Expand/collapse control:

EXPAND

Tabs:

- STATE
- QUESTION
- RESPONSE

The inspector is intended for technical viewers who want to inspect the exact observable data.

The default view should show a compact structured preview, for example:

- Turn 12
- Active Garchomp
- Legal actions 3

The expanded view may display more detailed structured content, but the normal dashboard should not become a wall of raw JSON.

## 8. Bottom action strip

The bottom strip contains three connected panels.

### Validate panel

Title:

VALIDATE

Source label:

ADAPTER

Visible elements:

- green success icon;
- validation status;
- selected action;
- small execution-time badge.

Example content:

- LEGAL ACTION
- MOVE_EARTHQUAKE is a valid move
- < 1 MS

### Act panel

Title:

ACT

Source label:

ENVIRONMENT

Visible elements:

- action arrow;
- submitted action;
- small execution-time badge;
- command status.

Example content:

- SEND MOVE_EARTHQUAKE
- Execute action command and await game response
- < 1 MS

### Result panel

Title:

RESULT

Source label:

SHOWDOWN

Visible elements:

- result icon;
- damage amount or range;
- target status;
- surviving/fainted state;
- next-state indicator;
- small execution-time badge.

Example content:

- 72–85% DAMAGE
- TARGET SURVIVES
- NEXT TURN STATE
- < 1 MS

These three panels should feel like a fast sequence after Jev returns.

## 9. Bottom status bar

Visible elements:

- current turn;
- selected Jev action;
- inference latency;
- damage result;
- target state;
- next-turn readiness;
- format;
- model identifier;
- observable-data indicator.

Example:

TURN 12 | Jev chose MOVE_EARTHQUAKE | 184 MS | Damage 72–85% | Target survives | Next turn state ready

This text is illustrative and may be shortened for readability.

## 10. Visual information ownership

The dashboard should visually distinguish where information comes from:

- SHOWDOWN STATE — observed battle information;
- CALCULATED BY HARNESS — deterministic derived facts;
- JEV OUTPUT — fields returned by Jev;
- ADAPTER — validation and action submission;
- SHOWDOWN — resulting game event.

These labels are important for transparency.

## 11. Visual states

The mockup should support visual variations for:

- idle before the first battle;
- ready to start;
- collecting battle state;
- calculating facts;
- waiting for Jev;
- Jev response received;
- validating action;
- sending action;
- showing result;
- battle won;
- battle lost;
- provider error;
- fallback action;
- reconnecting or waiting for the next turn.

These are visual states only in this document. Their actual behavior will be defined later.

## 12. Deliberately provisional elements

The following may need refinement after real data is available:

- exact Pokémon sprite style;
- exact font;
- exact color palette;
- panel dimensions;
- text length;
- action labels;
- damage display format;
- probability precision;
- latency display;
- cost display;
- team-row density;
- inspector content;
- responsive behavior;
- error-state wording.

The mockup is a shared visual target, not a promise that every displayed value or label will remain unchanged.

## 13. Final reference

The current visual reference is:

[dashboard-mockup-final.png](dashboard-mockup-final.png)

Previous iterations remain in the same folder for comparison:

- [dashboard-mockup-v2.png](dashboard-mockup-v2.png)
- [dashboard-mockup-v3.png](dashboard-mockup-v3.png)
- [dashboard-mockup-v4.png](dashboard-mockup-v4.png)
