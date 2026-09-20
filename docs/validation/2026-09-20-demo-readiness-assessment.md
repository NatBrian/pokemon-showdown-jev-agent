# Demo Readiness Assessment — Codex Takeover Verification

Date: 2026-09-20
Status: **verified MVP, with documented external-service limitations**

## Scope

This assessment records the current reproducible behavior after the Codex takeover repairs. It replaces the earlier assessment's official-client iframe claims. The MVP dashboard now uses the local arcade renderer as its primary battle view; it does not require a manually logged-in Showdown iframe.

## Backend verification

The project was installed into the repository-local environment:

```powershell
uv venv .venv --python 3.11
uv pip install --python .venv\Scripts\python.exe -e ".[dev]"
```

Fresh test command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result: **44 passed**.

Coverage includes the Jev client, candidate enumeration, Gen 9 type/damage facts, snapshot fog-of-war, validator/fallback behavior, battle-line scanning, orchestrator lifecycle, dashboard WebSocket behavior, and simulated end-to-end battle flow.

The suite still reports two dependency-level warnings from Starlette's current TestClient/anyio compatibility path. The application-level FastAPI `on_event` warning was removed by migrating the dashboard loop capture to a lifespan handler.

## Jev verification

- The configured route is OpenCode System One with model `jev-1.13-free`.
- The request is asynchronous and contains structured `state` plus a typed `choice` question with instructions and criteria.
- Live responses provide a typed choice, confidence, probability distribution, token usage, model, and cost.
- `TURN_DECISION` telemetry now preserves the exact request payload, typed response, validation result, and submitted Showdown order, without authorization headers or passwords.

## Browser verification

The dashboard was tested through Playwright at desktop viewport sizes and visually inspected from screenshots.

Verified states:

- clean idle page with `START JEV BATTLE`;
- local arcade battle renderer with active Pokémon, HP, status, own team, opponent fog-of-war slots, and turn history;
- Jev Input cards with state summary, field conditions, calculated facts, legal actions, and criteria text;
- Jev Output cards with model, confidence, probabilities, latency, tokens, and cost;
- technical inspector QUESTION tab showing the typed question and criteria;
- `VALIDATE → ACT → OBSERVED RESULT` strip;
- fallback banner: `JEV FAILED — FALLBACK USED` with the adapter-selected action;
- victory/defeat overlay and return to a retryable `START JEV BATTLE` state;
- zero browser console errors and zero browser console warnings during the verification run.

The current visual deliberately labels incomplete-information damage as an estimate. When the calculator has sufficient known battle state, the dashboard labels the result as a poke-env Gen 9 calculated range.

## Real public battle verification

One real public Gen 9 Random Battle was completed through the dashboard after the repairs:

- public Showdown matchmaking;
- Jev decisions made through the configured live API;
- local arcade renderer updated from live poke-env state;
- battle progressed through turn 13;
- real Showdown defeat event rendered in the result overlay;
- dismissing the overlay returned the dashboard to a ready state.

This proves the end-to-end path works. It does **not** establish Jev's overall skill, human-level performance, or a statistically meaningful win rate. Those require a future multi-battle benchmark campaign.

## Important limitations

- Public matchmaking depends on Showdown availability and a responsive human opponent.
- The free Jev route is provider-controlled and may have availability or rate limits.
- Random Battle opponent information is incomplete by design. Hidden items, abilities, moves, and exact stats must not be fabricated.
- The exact damage calculator is used only when the necessary battle state is available; otherwise the dashboard shows a bounded heuristic estimate.
- The benchmark command uses a configured Showdown-compatible server and real Jev calls; it is not an offline benchmark.
- The official Showdown iframe/proxy remains historical code and is not part of the default MVP dashboard path.

## Recording recommendation

Run the local server with the project interpreter, open the dashboard, click `START JEV BATTLE`, and record the idle → searching → Jev decision → battle → result sequence. The custom renderer is the reliable visual source for the Jev showcase; no iframe login step is required.
