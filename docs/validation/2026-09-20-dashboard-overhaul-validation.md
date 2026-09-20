# Dashboard Overhaul Validation

Date: 2026-09-20  
Target: local dashboard at `http://127.0.0.1:8000/`  
Format: public Pokémon Showdown Gen 9 Random Battles  
Execution: repository `.venv\Scripts\python.exe`

## Readiness rubric

| Area | Pass condition | Result |
| --- | --- | --- |
| Technical correctness | Static assets, JavaScript syntax, backend tests, and WebSocket lifecycle pass | PASS |
| End-to-end reliability | A real public match starts, receives turns, submits legal orders, and ends without a page/runtime failure | PASS |
| Official battle fidelity | The official Showdown renderer supplies the arena, sprites, HP/status HUD, team indicators, effects, messages, and final scene | PASS |
| Jev transparency | The visible rail is driven by actual Jev input/output and measured adapter fields | PASS |
| Temporal truth | Validate, act, and observed result remain separate and chronological | PASS |
| UX clarity | A mixed audience can identify the battle, harness input, Jev choice, and resulting action in the first viewport | PASS |
| Visual quality | Retro arcade shell, exact 16:9 battle bay, aligned rail, no duplicated game widgets, no normal-outcome modal | PASS |
| Degraded states | Jev fallback and renderer fallback are visibly attributed and distinguishable from Jev output | PASS |
| Technical inspection | One click opens state/request/response/validation/protocol JSON; Escape closes it | PASS |

## Automated checks

- `.venv\Scripts\python.exe -m pytest -q` → **56 passed, 2 existing dependency deprecation warnings**.
- `.venv\Scripts\python.exe -m pytest tests/unit/test_frontend_assets.py -q` → **8 passed**.
- `node --check src/jev_showdown/web/static/app.js` → **pass**.
- `node --check src/jev_showdown/web/static/showdown-renderer.js` → **pass**.
- The one stale HTTP title assertion was updated to the intentional `JEV BATTLE AGENT` title.

The warnings are from the installed FastAPI/Starlette test client dependency boundary; they do not originate in the dashboard runtime.

## Playwright visual and interaction checks

Playwright was set to `1440×900` and screenshots were inspected visually. The browser harness reported a scaled CSS viewport of `2160×1350` with `devicePixelRatio ≈ 0.667`; the screenshot output remained `1440×900`. The layout had no document scrolling at the recording viewport.

### Idle view

- Full-width battle-first layout uses the official-scene-sized 16:9 bay instead of an empty hidden stage.
- The idle bay shows `TELEMETRY FALLBACK / PRESS START TO LOAD SHOWDOWN SCENE` as an intentional state.
- The Jev rail contains only `JEV INPUT` and `JEV DECISION`.
- The bottom trace is `VALIDATE → ACT → OBSERVED RESULT`.
- No old slogans, history panel, duplicate teams, duplicate terrain/weather cards, or outcome modal appear.

### Synthetic telemetry lifecycle

A representative event using the real `TURN_DECISION` contract was published in the page:

- input summary showed turn, active matchup, field, legal-action count, top-K actions, and candidate facts;
- output showed selected typed choice, confidence, probability distribution, model, latency, usage, and cost;
- the selected action was highlighted;
- the trace moved to `LEGAL ACTION → SUBMITTED ... → AWAITING SHOWDOWN`;
- a valid protocol frame changed the result to an observed move/damage/faint/turn event;
- technical inspection opened from one click and exposed the JSON tabs;
- Escape closed the inspector;
- a fallback event displayed `JEV FALLBACK` and `FALLBACK USED` with its adapter reason and fallback action.

### Official Showdown scene

A valid init/switch/turn protocol replay rendered the real Showdown scene without an iframe. Visual inspection confirmed:

- official arena/background and perspective;
- real active Pokémon sprites and trainer sprites;
- HP bars, levels, type/status indicators, and team Poké Ball indicators;
- official scene messages and battle log inside the battle bay;
- no scene crop at the 16:9 host boundary.

The first intentionally minimal synthetic protocol fixture caused a Showdown parser message because it omitted required init/switch state. That was a fixture error, not a production failure. Replaying a valid protocol sequence rendered cleanly.

## Real public match

The dashboard `START JEV BATTLE` action was clicked against the configured `.env` account.

- Matchmaking reached `SHOWDOWN LIVE`.
- Jev reached `JEV ONLINE` and repeatedly produced decisions using model `jev-1.13-free`.
- Observed Jev inference latency ranged roughly from **518–981 ms** during the match.
- Observed usage included roughly **3.1k–4.1k input tokens** and **63–168 output tokens** per decision.
- Reported cost was **0** for the configured free model.
- Orders were validated and submitted across **24 turns**.
- Result: **VICTORY**; `1j_e_v1` won the battle.
- Final official Showdown scene remained visible after `BATTLE_END`.
- The normal outcome was rendered in the official scene/status trace; no modal appeared.
- No browser console errors were recorded during the real match.

Network inspection showed successful `200` responses for the local official Showdown bundle, battle CSS/JavaScript/data files, remote Showdown backgrounds, sprites, type icons, and move-effect assets.

## Runtime notes

- The server was launched with the repository `.venv` interpreter and the parent dashboard process was confirmed at `.venv\Scripts\python.exe`.
- The live match used the actual configured Jev/OpenCode path and public Showdown connection; no mock provider or simulated decision path was used.
- The test account and API credentials were not written into this document.

## Final checklist

- [x] First viewport is battle-first and readable.
- [x] Official renderer is the only game visual source.
- [x] Battle bay is exact 16:9 and has no separate below-stage log/status block.
- [x] Jev Input and Jev Decision are compact and non-duplicative.
- [x] Only actual Jev/adapter fields are shown; no chain-of-thought or invented scores.
- [x] `VALIDATE → ACT → OBSERVED RESULT` is truthful.
- [x] Fallback states are explicit.
- [x] Technical inspection is hidden by default and single-click accessible.
- [x] Real public match completed autonomously.
- [x] Final scene was preserved after battle end.
- [x] Automated tests and browser checks passed.
