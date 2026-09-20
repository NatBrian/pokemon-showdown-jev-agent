# Dashboard rewrite validation

Date: 2026-09-20

## Automated checks

Using the repository virtual environment:

```powershell
C:\Users\Admin\Documents\Github\autonomous-pokemon-showdown-jev-agent\.venv\Scripts\python.exe -m pytest -q
```

Result: `59 passed, 2 warnings`.

The warnings are the existing Starlette/httpx and anyio deprecation warnings from the installed test dependencies. No new application warning was introduced.

Focused frontend checks also passed:

```powershell
C:\Users\Admin\Documents\Github\autonomous-pokemon-showdown-jev-agent\.venv\Scripts\python.exe -m pytest tests/unit/test_frontend_assets.py -q
node --check src/jev_showdown/web/static/app.js
```

Result: `5 passed`; JavaScript syntax check passed.

## Browser setup and viewport evidence

The dashboard was served from the implementation worktree with:

```powershell
$env:PYTHONPATH = 'C:\Users\Admin\Documents\Github\_codex_worktrees\dashboard-rewrite\src'
C:\Users\Admin\Documents\Github\autonomous-pokemon-showdown-jev-agent\.venv\Scripts\python.exe -m jev_showdown.main serve --port 8010
```

The configured-environment smoke used port `8011` because port `8000` was already occupied. Playwright used Chromium with explicit desktop viewports of `1440x900` and `1600x900`.

Screenshots:

- [1440x900 idle view](assets/dashboard-1440.png)
- [1600x900 idle view](assets/dashboard-1600.png)
- [1440x900 startup/error state](assets/dashboard-live-start.png)
- [1440x900 Playwright capture](assets/dashboard-playwright-1440.png)

At `1440x900`, the browser reported `document.body.scrollHeight = 900` and `document.body.scrollWidth = 1440`. At `1600x900`, the same single-screen composition was visible: one direct-mounted official Showdown scene, Jev input/decision/history rail, compact truth strip, and one start control. Chromium reported no console errors, page errors, or failed asset requests during the idle render.

## Controlled browser message-sequence checks

The exported `window.JevDashboard` factory was exercised with a fake WebSocket and renderer at `1440x900`:

- `DECISION_PHASE.JEV_EVALUATING` rendered `EVALUATING` only in the Jev decision panel.
- `TURN_DECISION` rendered the typed choice, real confidence/probabilities/model/latency, and one history row.
- `ORDER_SUBMITTED` preserved the exact `|/choose ...` order in the adapter trace.
- `AWAITING_SHOWDOWN` remained pending until a frame containing `|move|` arrived; then the trace became `RESULT OBSERVED` and `observed_commands` was `['move']`.
- Technical inspection contained the current snapshot and request record.
- A fallback decision rendered `FALLBACK USED` with its adapter action/reason and did not render a `SELECTED` Jev row.
- `BATTLE_END` called `renderer.end()`, kept the history row, and left the phase at `RESULT_OBSERVED`.
- `BATTLE_REPLAY` reset the renderer even when the battle tag was unchanged, fed replay frames in order, and kept the Jev history intact.
- A rejecting renderer mount exposed `OFFICIAL SHOWDOWN RENDERER UNAVAILABLE - TELEMETRY FALLBACK ACTIVE` while leaving the telemetry DOM available.

## Configured-environment startup smoke

The dashboard WebSocket accepted `START_BATTLE` and returned the backend's explicit status:

```text
ERROR: SHOWDOWN ACCOUNT NOT CONFIGURED - SET SHOWDOWN_USERNAME / SHOWDOWN_PASSWORD IN .env
```

The checked `.env` variable names were not copied into the dashboard or validation artifact, and no credentials were exposed. Because the configured values are placeholders/non-usable for public matchmaking, this environment could not produce a real public battle, Jev response, turn count, or honest battle outcome. The UI displayed `SHOWDOWN ERROR` and returned the start control to its ready state rather than manufacturing a battle state.

The direct official renderer itself loaded its local bundle and assets successfully in the browser. A real account-backed battle should be rerun with valid configured Showdown credentials to collect live `JEV_EVALUATING`, `TURN_DECISION`, `RESULT_OBSERVED`, and battle-end evidence.
