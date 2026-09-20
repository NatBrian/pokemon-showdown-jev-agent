# Final Pokémon Battle UI Visual Direction

Status: `FINAL RENDERER DIRECTION / RASTER MOCKUP REMOVED`

Date: `2026-09-20`

## Final decision

The live battle area should use the official Pokémon Showdown battle renderer, not a hand-built approximation of Pokémon battle effects.

The visual target is:

> **A polished Pokémon Black/White-inspired 2D/2.5D battle presentation, powered by the official Showdown renderer and surrounded by a transparent Jev observability cockpit.**

This gives the project the recognizable battle feel of a real Pokémon game while keeping the purpose of the demo visible: what the harness calculated, what Jev decided, what was validated, what was submitted, and what Showdown actually returned.

## Asset inventory

### Pokémon and team assets

Showdown hosts multiple sprite families under its official sprite directory:

- animated front and back sprites (`ani`, `ani-back`);
- animated XY-style sprites (`xyani`, `xyani-back`);
- static battle sprites (`gen5`, `gen5-back`, and other generation families);
- shiny variants;
- team icons, Poké Ball indicators, type icons, and item icons.

The official battle renderer chooses the appropriate sprite and positions it on the battle scene. We should let it own sprite selection rather than maintaining a second species/form mapping in our dashboard.

### Arena and background assets

The official FX directory contains:

- neutral battle backgrounds;
- generation-style arenas;
- cave, forest, beach, desert, mountain, snow, water, city, and stadium scenes;
- client background textures and battle backdrop layers.

The battle renderer composes these as a background layer behind the Pokémon and status UI.

### Weather and terrain assets

Available official layers include:

- rain and rain-dance;
- sandstorm;
- sun/sunny day;
- hail/snow;
- electric terrain;
- grassy terrain;
- misty terrain;
- psychic terrain;
- gravity, trick room, magic room, wonder room, and strong wind.

Some are raster overlays and some are short video assets. For the first implementation, the renderer’s existing behavior should be used; video/audio expansion is unnecessary for the showcase MVP.

### Move and battle-effect assets

The official FX collection includes reusable effect layers such as:

- impact and hit markers;
- fireballs, blue fire, flare effects, and wisps;
- electroball and lightning;
- energy ball, shadow ball, mist ball, and water effects;
- iceballs and icicles;
- rocks, leaves, petals, feathers, fists, feet, claws, swords, and slashes;
- flashes, shines, status indicators, faint effects, hazards, and Poké Ball effects.

The official client maps individual move protocol events to these effects through its battle animation tables. The project should reuse that mapping instead of maintaining a simplified move-type animation table.

### UI assets and layout primitives

The renderer also supplies:

- Pokémon HP/stat bars;
- team-side indicators;
- move/effect message bar;
- battle log typography;
- status, boost, hazard, and effectiveness markers;
- transition and faint animations.

These are more authentic and more reliable than recreating them with custom HTML cards.

## Style classification

The asset system is not 3D. It is a layered 2D renderer that creates a 2.5D impression:

| Layer | Visual technology | Result |
| --- | --- | --- |
| Pokémon | 2D raster sprites, including animated sprite assets | Flat animated character art |
| Arena | 2D background images with perspective platforms | Depth and spatial staging |
| Weather/terrain | 2D overlays and optional short video textures | Environmental motion |
| Move effects | 2D raster effects composed above the scene | Impact, color, and action feedback |
| UI | DOM/CSS positioning and animation | Game HUD and readable state |
| 3D models | Not used | No real-time 3D engine or WebGL required |

Therefore the correct description is **2D assets presented in a 2.5D battle composition**, not pixel art in the strict retro sense and not 3D.

## Which Pokémon generation is the best visual match?

| Generation/style | Match to available assets | Decision |
| --- | --- | --- |
| Generations I–III | Mostly static sprite presentation and simpler effects | Too limited for the desired live showcase |
| Generation IV / Diamond & Pearl | Strong 2D battle layout, but less expressive sprite motion | Good fallback, not the best match |
| Generation V / Black & White | Animated 2D sprites, dynamic battle framing, readable HUD, strong effect language | **Best mainline-generation style match** |
| Generations VI–IX | Primarily 3D-model presentation in the games | Poor match for the available 2D Showdown asset system |
| Official Pokémon Showdown client | Exact source of the available scene, animation, and protocol integration | **Best technical implementation target** |

The final visual direction is intentionally a hybrid: use the official Showdown renderer and assets, with a presentation that feels closest to Black/White rather than pretending to be a 3D X/Y or Sun/Moon battle.

## Final screen composition

### 1. Live battle stage — left side, visual focus

- Official Showdown arena background and perspective platforms.
- Animated front/back Pokémon sprites.
- Real HP bars, levels, status markers, and team indicators.
- Persistent weather and terrain visuals when reported by Showdown.
- Official move effects, hit reactions, switch animations, faint animations, effectiveness markers, and Terastallization effects.
- Compact battle message bar for the latest observed event.
- No chat, ads, matchmaking controls, or unrelated Showdown website chrome.

### 2. Jev Input — right upper panel

This is the harness side of the story:

- active Pokémon and HP;
- known team members and fog-of-war placeholders;
- weather, terrain, hazards, and Tera availability;
- legal actions;
- deterministic calculated facts such as type effectiveness, damage range, KO risk, speed comparison, and switch cost.

### 3. Jev Output — right lower panel

This is the model side of the story:

- model identity;
- selected action;
- confidence;
- probability distribution over legal actions;
- latency, usage, and reported cost;
- explicit fallback warning when Jev fails.

### 4. Decision truth strip — bottom

```text
VALIDATE  →  ACT  →  OBSERVED RESULT
```

- **VALIDATE:** the selected Jev output is checked against legal Showdown actions.
- **ACT:** the exact `/choose ...` order is submitted.
- **OBSERVED RESULT:** the result is rendered only after Showdown reports the outcome.

The effect layer must be driven by the same observed protocol stream. It must never invent a successful hit, damage amount, terrain, or weather state merely because Jev selected a move.

## Visual treatment

- The arena uses the official Showdown visual language: deep blue/neutral stadium backdrops, readable HP bars, soft field perspective, animated raster sprites, and layered effects.
- The outer dashboard keeps a restrained digital/arcade accent so the project still feels like an autonomous-agent showcase.
- The arena itself should not be overlaid with excessive neon or dense technical text.
- Technical transparency belongs in the Jev Input/Output panels and bottom strip, not on top of the Pokémon sprites.
- The dashboard should remain understandable when recorded at desktop 16:9 resolution.

## What we will reuse versus rebuild

### Reuse

- official `Battle` renderer;
- official renderer CSS and data files;
- official Pokémon sprites;
- official backgrounds, weather, terrain, and FX;
- official protocol-to-animation mapping;
- official HP/stat/status/team presentation where it fits the arena.

### Keep custom

- Jev Input panel;
- Jev Output panel;
- validation/action/result strip;
- fallback banner and failure transparency;
- dashboard header and minimal recording-oriented framing.

### Do not include

- full Showdown website window;
- iframe embedding;
- chat and advertisements;
- duplicate hand-built move animation system;
- a 3D engine;
- sound as an MVP dependency.

## Mockup

The former raster mockup was intentionally removed. Use the textual direction
and binding rules below instead.

The mockup is a visual direction reference, not a pixel-perfect implementation specification. The actual renderer will use real Showdown assets and protocol timing, so exact Pokémon, move effects, weather, and text will vary from battle to battle.

For the current dashboard redesign, see the binding implementation rules in
[`dashboard-redesign-guardrails.md`](dashboard-redesign-guardrails.md). The
generated mockup must not be copied literally: the official Showdown
renderer owns game visuals, Jev Output must use actual provider data, and
`OBSERVED RESULT` must reflect the protocol result of the submitted order.

## Research references

- [Official Pokémon Showdown client](https://github.com/smogon/pokemon-showdown-client)
- [Official Pokémon Showdown battle protocol](https://github.com/smogon/pokemon-showdown/blob/master/sim/SIM-PROTOCOL.md)
- [Official Pokémon Showdown sprites](https://play.pokemonshowdown.com/sprites/)
- [Official Pokémon Showdown FX assets](https://play.pokemonshowdown.com/fx/)
- [Nidozo Showdown battle scene integration](https://github.com/haggyroth/nidozo/blob/main/frontend/src/components/ShowdownBattleScene.jsx)
