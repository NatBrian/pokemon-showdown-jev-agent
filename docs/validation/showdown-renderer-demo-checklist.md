# Official Showdown Renderer Demo Validation

Date: `2026-09-20`

Status: `PASS — real local browser validation completed`

## Validation setup

- [x] Repository-local Python environment used: `.venv\Scripts\python.exe`.
- [x] Dashboard command used: `python -m jev_showdown.main serve --port 8000`.
- [x] Browser target: `http://127.0.0.1:8000/`.
- [x] Browser validation performed with Playwright MCP at a requested `1600×1000` viewport.
- [x] Battle format: `gen9randombattle`.
- [x] Jev endpoint/model observed in the live dashboard: OpenCode System One / `jev-1.13-free`.
- [x] Enemy source: real public Pokémon Showdown ladder opponent.
- [x] Renderer source: audited official Pokémon Showdown battle renderer subset in `src/jev_showdown/web/static/showdown/`.
- [x] Cosmetic source: official Showdown sprites, backgrounds, weather, and FX hosted under `play.pokemonshowdown.com`.

## Automated correctness

- [x] Raw Showdown frames are emitted from `JevPlayer` after battle-room filtering.
- [x] Frame replay is bounded to 400 protocol batches.
- [x] New dashboard connections receive `BATTLE_REPLAY` while a battle is active.
- [x] Empty, malformed, keepalive, and non-battle lines are filtered before browser delivery.
- [x] Official renderer scripts load in dependency order and `window.Battle` initializes.
- [x] No iframe is present in the dashboard HTML.
- [x] The custom arena remains a telemetry fallback only.
- [x] Test command: `.venv\Scripts\python.exe -m pytest -q`.
- [x] Result: `60 passed, 2 dependency deprecation warnings`.
- [x] JavaScript syntax checks passed with `node --check` for `app.js` and `showdown-renderer.js`.

## Real end-to-end battle evidence

- [x] First live run completed in `2` turns with a real Jev decision and `VICTORY`.
- [x] Second live run completed in `27` turns with a real Jev decision and `DEFEAT`.
- [x] The dashboard showed a real model response, confidence, probability distribution, legal actions, latency, validation, submitted action, and observed history during the second run.
- [x] The official battle stage showed real opposing/player sprites, trainer sprites, team Poké Ball indicators, HP bars, a Showdown arena background, battle turn label, and the official battle message log.
- [x] A live captured state showed Jev selecting `MOVE_HEADSMASH_TERA`; the official stage and telemetry panels updated in the same browser session.
- [x] Post-battle state showed `BATTLE ENDED … RESULT OBSERVED FROM SHOWDOWN`, preserved the final official scene, and rendered the actual `DEFEAT` result.
- [x] A late protocol frame after `BATTLE_END` did not overwrite the final-scene status.

## Browser/runtime signals

- [x] Dashboard WebSocket connected successfully.
- [x] Static renderer assets returned `200`/`304` responses.
- [x] Official FX and sprite requests returned successful responses for the live battle assets used in the captured run.
- [x] Browser console contained `0` errors and `0` warnings during the final synthetic/post-battle state check and the live battle page.
- [x] FastAPI process remained alive throughout the live battle and served the page/assets normally.
- [x] The server logs showed accepted `/ws` connections and successful static renderer requests.

## Visual and storytelling rubric

- [x] Battle stage is the visual focus on a 16:9 recording viewport.
- [x] The stage uses authentic Showdown 2D/2.5D sprites, arena, trainer/team HUD, HP bars, message log, and renderer-driven animation layers.
- [x] Jev Input is visibly separated from Jev Output.
- [x] Calculated facts are labelled as harness-owned; inference is labelled as model-owned.
- [x] The bottom strip communicates `VALIDATE → ACT → OBSERVED RESULT`.
- [x] The result panel does not claim an outcome before Showdown reports it.
- [x] Fallback behavior is visible and explicitly attributed to the renderer adapter, not Jev.
- [x] Technical viewers can inspect state, question/criteria, and response data without making raw JSON the primary experience.
- [x] Non-technical viewers can follow the battle, model choice, confidence, action, and observed outcome without reading the inspector.
- [x] No chat, ads, matchmaking UI, or unrelated Showdown website chrome is present.

## Known non-blocking caveats

- [ ] Some rare form-specific cosmetic sprite URLs may be rejected by a browser resource policy or may be absent from the public CDN; the official renderer still preserves its battle HUD and the existing fallback remains available. The captured live battle used valid official assets.
- [ ] The test suite retains the two existing dependency deprecation warnings from Starlette/httpx and anyio; they are not application runtime failures.

## Recording readiness decision

The local demo is ready to record: it runs the real Jev/OpenCode path, joins a real Gen 9 Random Battle, renders the official Showdown battle scene, exposes the Jev decision evidence, and preserves truthful observed results. Start the server, open the local URL, and click `START JEV BATTLE`.
