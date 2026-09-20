# GitHub Research: Reusing the Pokémon Showdown Battle Renderer

Date: `2026-09-20`

## Executive conclusion

Yes, another project has already solved the hardest visual part: mounting the official Pokémon Showdown battle scene inside a separate AI dashboard.

The closest reference is [haggyroth/nidozo](https://github.com/haggyroth/nidozo). Its frontend:

1. loads a small, vendored subset of the Pokémon Showdown client;
2. creates the official browser-global `Battle` renderer;
3. opens a WebSocket carrying raw Showdown battle protocol;
4. feeds each protocol line to `battle.add(line)`;
5. calls `battle.play()` so the official scene renders Pokémon, HP bars, backgrounds, switches, move animations, weather, terrain, effects, and the battle log;
6. places model-analysis panels around the scene in a “Showdown cockpit.”

This is much closer to the requested dashboard than recreating all effects with CSS. We should reuse this proven renderer pattern, not copy the entire Nidozo application and not rebuild Pokémon battle animations ourselves.

## Candidate projects

### 1. Nidozo — closest match

Repository: [haggyroth/nidozo](https://github.com/haggyroth/nidozo)

Relevant files:

- [ShowdownBattleScene.jsx](https://github.com/haggyroth/nidozo/blob/main/frontend/src/components/ShowdownBattleScene.jsx)
- [useShowdownBundle.js](https://github.com/haggyroth/nidozo/blob/main/frontend/src/hooks/useShowdownBundle.js)
- `frontend/public/showdown/` — the vendored renderer/data/CSS subset
- [Nidozo README battle cockpit](https://github.com/haggyroth/nidozo#the-battle-view--showdown-cockpit)

The checked-out reference bundle contained 17 files and approximately 2.93 MB: the renderer JavaScript, jQuery/polyfills, battle data, tooltips, and Showdown battle styles. Pokémon sprites and some effects are still loaded from the official CDN.

Why it is useful:

- It proves the official battle scene can run inside a dashboard without an iframe.
- It uses the actual Showdown renderer, so animations and effects are not approximations.
- Its `ShowdownBattleScene` component is an isolated integration boundary.
- Its analytics cockpit layout is conceptually similar to our Jev Input/Output dashboard.

Why it is not copy-pasteable as a whole:

- It is a React/Vite application; our dashboard is static HTML/CSS/JavaScript served by FastAPI.
- It expects a spectator WebSocket endpoint that replays raw battle protocol lines.
- It includes an LLM battle system, tournaments, database, replay, and other features that are outside our scope.
- Its vendored files and license/attribution need to be audited before copying them into another repository.

### 2. ps-local — real client plus helper panel

Repository: [AbhishekR3/ps-local](https://github.com/AbhishekR3/ps-local)

This project wraps the live `play.pokemonshowdown.com` client in an Electron `WebContentsView` and docks a React helper panel beside it. It is a strong reference for observing the real client, tapping its WebSocket, and placing analysis beside a battle.

It is not the right implementation for this project because:

- it is an Electron desktop application, while our target is a local browser dashboard;
- it shows the complete Showdown client rather than only the battle stage;
- it introduces a Node/Electron runtime and a larger packaging path;
- it solves a different problem: assisting a human playing in the official client.

Useful lesson: a battle helper should consume the same raw protocol stream as the renderer, rather than trying to infer animations from screenshots or from a partially updated state object.

### 3. Official Pokémon Showdown client — source of truth

Repository: [smogon/pokemon-showdown-client](https://github.com/smogon/pokemon-showdown-client)

The official client contains the real scene implementation in `battle-animations.ts` and `battle-animations-moves.ts`. Its battle scene has separate layers for the backdrop, terrain, weather, background effects, sprites, foreground effects, sidebars, and battle messages.

The official repository is the source of truth, but it is not a small drop-in widget. It is a complete client codebase, has a build process, and intentionally excludes some hosted resource directories such as sprites and audio.

The current official README states that the client is distributed under AGPLv3 and asks developers doing more than a normal fork to contact the copyright holder about relicensing. Therefore we must not blindly copy current client source into the project without checking the exact revision, preserving notices, and deciding how the project will satisfy the applicable license.

### 4. poke-env and other bot repositories

[poke-env](https://github.com/hsahovic/poke-env) is the correct battle harness for the Python agent, but it is not a browser renderer. Bot repositories generally provide decision logic and protocol handling, not an isolated animated battle scene.

## Recommended reuse strategy

Use Nidozo’s renderer integration pattern as a reference and port only the minimum required boundary:

```text
Showdown protocol from poke-env
        ↓
backend frame buffer + existing dashboard WebSocket
        ↓
official browser-global Battle renderer
        ↓
real Showdown arena, sprites, HP bars, terrain, weather, effects, animations
        +
Jev Input / Jev Output / validation / action telemetry beside it
```

The project should not copy:

- Nidozo’s LLM providers;
- its tournament/database/replay system;
- ps-local’s Electron shell;
- the complete Showdown website or an iframe;
- a second battle engine.

The likely implementation boundary is:

1. Add a small `showdown-renderer` static asset directory containing the audited renderer subset and attribution notice.
2. Load its scripts in the required order from the dashboard page.
3. Create one official `Battle` instance inside the current arena panel.
4. Extend the existing backend WebSocket event stream with raw battle protocol frames and a short replay buffer so the renderer can initialize even if it attaches after battle start.
5. Keep the current Jev telemetry panels unchanged around the arena.
6. Remove or minimize the duplicate custom active-Pokémon arena only after the official renderer is proven live.

This gives the audience the actual Pokémon Showdown battle presentation while keeping Jev’s decision pipeline visible and attributable.

## Main risks to resolve before implementation

### License and attribution

The official current client repository states AGPLv3, while Nidozo’s checked-in `NOTICE.md` describes its fetched legacy bundle as MIT. Those statements refer to different revisions/assets and must not be treated as interchangeable. Before vendoring code, identify the exact upstream files and revision, preserve the applicable notices, and document the result.

### Raw protocol availability

Our backend currently publishes summarized `TURN_DECISION` telemetry. The official renderer needs raw battle lines such as `|start`, `|switch`, `|move`, `|-damage`, `|-weather`, `|-fieldstart`, `|-supereffective`, and `|faint`. The simplest reliable solution is to publish the raw lines already received by `poke-env`, with a bounded per-battle replay buffer.

### Duplicate state presentation

The official renderer already draws Pokémon, HP bars, team indicators, effects,
and a battle log. Keeping every existing custom battle card beside it would
create duplication and reduce visual clarity. The custom surface must therefore
remain an observability layer around the official renderer, while its exact
composition is intentionally left open. Preserve the source-of-truth and
decision-data rules in
[dashboard-product-contract.md](../design/dashboard-product-contract.md).

## Recommendation

Do not copy-paste an entire third-party project. Copy the proven *integration pattern* from Nidozo, audit and reuse the minimum official renderer subset, and connect it to our existing real Showdown protocol stream. This is the fastest route to authentic Pokémon battle visuals while keeping the project simple, transparent, and Jev-focused.
