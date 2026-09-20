# End-to-End Demo Validation Assessment

Status: `DEMO READY — VERIFIED FOR LOCAL RECORDING`

Date: `2026-09-20`

This document records fresh runtime evidence for the actual OpenCode Jev + Pokémon Showdown + dashboard path. It is intentionally separate from the earlier implementation validation report. The assessment validates that the local demo works; it does not claim statistically significant competitive strength from a handful of matches.

## Scope and acceptance criteria

The demo is considered ready when all of the following are true:

- the project runs from its repository-local `.venv` with no Hermes dependency;
- the configured Jev adapter calls the real OpenCode System One endpoint and returns a typed decision;
- a real `gen9randombattle` is played through Showdown and legal orders are submitted;
- the dashboard reflects the real battle state, Jev input, Jev output, validation, submitted action, and observed result;
- Jev failure is visible and the deterministic fallback keeps the battle moving;
- a viewer can understand the story from the rendered dashboard without reading backend code;
- no material browser, backend, or asset failures were observed during validation.

## Rubric

| Area | Result | Evidence and assessment |
| --- | --- | --- |
| Technical correctness | **PASS** | Live decisions came from `jev-1.13-free` through the configured OpenCode route. The adapter returned typed categorical choices with confidence/probabilities, the validator accepted legal candidates, and `/choose ...` orders reached Showdown. |
| End-to-end reliability | **PASS** | Three real public-match Jev battles completed through the dashboard, including 32-turn defeat, 20-turn victory, and 18-turn defeat runs. A separate Jev-timeout run completed 14 turns using fallback orders. |
| State fidelity | **PASS** | The dashboard showed active Pokémon, HP, known/unknown team information, legal actions, calculated facts, criteria, Jev probabilities, selected action, exact submitted order, and Showdown’s final observed result. |
| Real-time behavior | **PASS** | WebSocket updates advanced the UI through multiple turns while Jev requests were in flight. Observed live decision latencies were approximately 522–1054 ms; the backend remained connected and responsive. |
| UX clarity | **PASS** | The three-column layout explains the story as `battle state → Jev input → Jev output`, followed by `validate → act → observed result`. Technical details are visible without making the viewer inspect raw logs. |
| Visual quality | **PASS** | Playwright screenshots were reviewed visually at the recording-oriented desktop viewport. The arcade-retro treatment is coherent, the battle stage is readable, and official animated Showdown sprites are used for active and team Pokémon. |
| Runtime hygiene | **PASS** | No browser console errors or warnings, no failed Pokémon images after the asset fix, no iframe embedding, no traceback in the observed server logs, and no secret values were printed. |
| Evidence quality | **PASS** | Evidence includes project-local environment checks, unit tests, live Jev battles, a failure-path battle, Playwright snapshots/screenshots, DOM assertions, console/network checks, and server logs. |

## Environment and preflight evidence

All commands were run from:

```text
C:\Users\Admin\Documents\Github\autonomous-pokemon-showdown-jev-agent
```

The project-local interpreter was used:

```text
.venv\Scripts\python.exe
Python 3.11.9
uv 0.11.16
```

Passed checks:

```text
uv lock --check                         Resolved 47 packages
.venv\Scripts\python.exe -m compileall -q src
pytest -q                               44 passed, 2 dependency warnings
```

After the validation fixes and new regression checks, the complete suite finished with:

```text
pytest -q                               46 passed, 2 dependency warnings
git diff --check                        passed
```

The environment file was inspected by key name only. It contains the expected Showdown, Jev, format, and dashboard settings; secret values were not emitted. The documented live Jev configuration is:

```text
POST https://opencode.ai/zen/v1/systemone
Model: jev-1.13-free
Format: gen9randombattle
```

The application uses the asynchronous Jev adapter directly rather than routing decisions through a conversational chat loop.

## Live Jev and Showdown evidence

### Production path

The backend was started with:

```powershell
.\.venv\Scripts\python.exe -m jev_showdown.main serve --port 8123
```

The server started normally on `http://127.0.0.1:8123`, served the dashboard, accepted the WebSocket, authenticated to Showdown, and continued through battle lifecycle events.

Three real public matchmaking battles were observed on the production path:

1. **Defeat, 32 turns.** Live Jev decisions were visible with roughly 522–968 ms latency, reported input/output usage, and `$0` reported cost.
2. **Victory, 20 turns.** The dashboard displayed the live battle with official Showdown sprites and completed the battle overlay.
3. **Defeat, 18 turns.** The final-code path displayed a live Jev decision, received the Showdown battle-end event, changed the bottom strip to `DEFEAT`, and retained `BATTLE ENDED AFTER 18 TURNS • RESULT OBSERVED FROM SHOWDOWN` after the overlay was dismissed.

The observed public opponents were obtained through public matchmaking. No built-in Showdown bot identity was verified, so this evidence does not claim a reproducible difficulty ladder or bot benchmark.

### Failure path

A temporary validation server was run with an intentionally unreachable Jev endpoint and a 0.5-second timeout. The application did not crash or stall:

- the dashboard displayed `JEV FAILED — FALLBACK USED`;
- the fallback reason was visible;
- the fallback action was shown and marked `FALLBACK VALIDATED`;
- the exact fallback `/choose ...` order was shown;
- the real Showdown battle continued to turn 14 and ended normally.

This verifies the safety behavior, not the quality of a Jev decision.

## Dashboard and Playwright evidence

The dashboard was inspected as rendered UI, not only by reading source code. The following states were exercised:

- idle/ready state;
- active live battle with multiple turns;
- Jev input with calculated facts and legal actions;
- Jev output with model label, confidence, probabilities, criteria, latency, usage, and cost;
- validation and exact action submission;
- Jev failure/fallback state;
- battle-end overlay and dismissed observed-result state;
- reset/start path used for subsequent battles;
- narrow responsive viewport.

Important browser assertions:

```text
iframe count: 0
failed Pokémon images after sprite fix: []
browser console errors: 0
browser console warnings: 0
desktop CSS viewport: 1280 x 900
narrow CSS viewport: 760 x 900, no horizontal overflow
```

The visual review found a clear arcade-retro hierarchy: the battle stage is the focal point, the middle panel explains what the harness calculated, the Jev panel explains the model decision, and the bottom strip makes validation/action/result causality explicit. Official animated front/back Showdown sprites are visible in the battle stage and team rows.

Validation screenshots were captured outside the repository during the run, including:

```text
e2e-dashboard-idle.png
e2e-dashboard-turn-1.png
e2e-dashboard-turn-15.png
e2e-dashboard-official-assets.png
e2e-dashboard-victory-official-assets.png
e2e-dashboard-fallback-after-dismiss.png
e2e-dashboard-final-result.png
e2e-dashboard-narrow.png
```

## Findings and fixes

### Official Pokémon assets

The original dashboard used a third-party sprite URL and could show a failed image for compact Showdown form identifiers. The renderer now uses the official hosted Showdown sprite directories:

- [Pokémon Showdown animated sprites](https://play.pokemonshowdown.com/sprites/xyani/)
- [Smogon sprite repository](https://github.com/smogon/sprites)

The custom dashboard still avoids embedding the full Showdown client UI. It uses front sprites for the opponent, back sprites for the agent’s active Pokémon, team sprites, and an initials fallback when a particular asset is unavailable. Form normalization handles identifiers such as compact Alola forms. Playwright confirmed loaded official sprite URLs with non-zero natural widths and no failed images.

### Truthful post-battle result

The bottom result strip previously represented the last turn’s action and could remain visually stale after the modal closed. It now updates from the actual Showdown battle-end event, explicitly says `OBSERVED RESULT`, shows `BATTLE ENDED ... RESULT OBSERVED FROM SHOWDOWN`, and changes victory styling when the agent wins.

### Regression coverage

Focused frontend tests now assert that official Showdown sprites are used without an iframe and that the observed post-battle result is represented in the dashboard. The full existing suite remained green after the fixes.

## Limitations and honest interpretation

- Public matchmaking does not provide a deterministic opponent difficulty ladder. A built-in difficult Showdown bot was not verified during this validation. Reproducible bot baselines remain future benchmark work.
- Three completed Jev matches are enough to validate the pipeline, not enough to establish a statistically significant win rate or a claim that Jev is human-level.
- The dashboard uses official sprites and a custom battle stage; it does not embed the entire Showdown client, so full client move animations, sound effects, chat, and replay controls are intentionally absent.
- Damage and matchup facts are harness calculations/heuristics under imperfect information. The UI labels the Jev input as calculated facts rather than presenting hidden information as certain.
- The test stack emits two dependency-level deprecation warnings from Starlette/httpx/anyio. They did not cause runtime failures and are not dashboard defects.
- The demo requires network access for the OpenCode Jev endpoint, Pokémon Showdown, and hosted sprite assets, plus valid credentials in the local `.env`.

## Final decision

**Ready for a local recording and LinkedIn demo.** The actual Jev → legal validation → Showdown order → observed result path was demonstrated, the fallback path was exercised, and the rendered dashboard was visually reviewed. Keep the claims scoped to demonstrating the decision pipeline and this implementation’s observed matches; do not present the small sample as a competitive benchmark.

Recommended recording command:

```powershell
cd C:\Users\Admin\Documents\Github\autonomous-pokemon-showdown-jev-agent
.\.venv\Scripts\python.exe -m jev_showdown.main serve --port 8123
```

Open `http://127.0.0.1:8123/` and click **START JEV BATTLE**.
