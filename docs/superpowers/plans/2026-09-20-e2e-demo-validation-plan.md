# End-to-End Demo Validation Plan

Status: `EXECUTED — SEE docs/validation/2026-09-20-e2e-demo-validation.md`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to execute this validation task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Prove, with fresh runtime evidence, that the local dashboard, backend, actual OpenCode Jev API, and live Pokémon Showdown battle work together reliably and are suitable for a recorded demo.

**Architecture:** Run the repository with its project-local `.venv`, start the FastAPI/WebSocket dashboard, use the configured OpenCode System One Jev route, and start a real Gen 9 Random Battle through poke-env. Observe the rendered dashboard with Playwright screenshots and browser telemetry while correlating UI state with backend logs, WebSocket messages, Jev HTTP requests, and Showdown battle events. Fix only issues that materially affect correctness, reliability, clarity, or demo quality.

**Tech Stack:** Python 3.11, uv, FastAPI, WebSocket, poke-env, OpenCode System One Jev endpoint, Pokémon Showdown, Playwright MCP, PowerShell.

**Spec:** `docs/research/phase-0-jev-opencode.md`, the existing dashboard documentation, and the acceptance criteria in this user request.

## Global Constraints

- Use `C:\Users\Admin\Documents\Github\autonomous-pokemon-showdown-jev-agent\.venv\Scripts\python.exe`; do not use Hermes.
- Use the actual configured Jev/OpenCode route; do not replace it with a mock or simulated decision path.
- Use a real Showdown battle and preserve fog-of-war and legal-order behavior.
- Inspect the dashboard visually with Playwright screenshots at the recording-oriented viewport.
- Do not expose `.env` secrets in logs, screenshots, telemetry, or the final report.
- Keep the solution simple; do not add a second dashboard or a large asset pipeline unless the current UI cannot satisfy the demo goal.

## Assessment Rubric

- Technical correctness: Jev request succeeds, typed response is mapped to a legal order, and the submitted order reaches Showdown.
- End-to-end reliability: backend stays alive through startup, matchmaking, multiple turns, battle end, retry, and shutdown without silent failures.
- State fidelity: dashboard state, criteria, response, selected action, observed result, teams, fog-of-war, and costs correspond to actual runtime events.
- Real-time behavior: WebSocket updates arrive promptly, the UI does not freeze, and timers/status do not become misleading during Jev latency.
- UX clarity: a non-technical viewer can understand what the agent sees, what Jev evaluated, what action was submitted, and what actually happened.
- Visual quality: the arcade layout is coherent at the recording viewport, assets are sharp enough, text is readable, and no stale/empty panel competes with the battle.
- Runtime hygiene: no meaningful console errors, uncaught exceptions, malformed requests, secret leakage, or orphaned project processes.
- Evidence quality: each pass/fail is supported by a command, log, network observation, screenshot, or reproducible browser assertion.

## Review Focus

- Actual Jev route versus mocked/synthetic decisions; verify the response has live usage/cost and is recorded in telemetry.
- Showdown account/matchmaking/authentication and battle lifecycle; distinguish network waiting from application failure.
- Dashboard update ordering; ensure prediction is not shown as an observed result before Showdown resolves the turn.
- Visual treatment of Pokémon sprites, battle stage, team information, fog-of-war, and compact technical inspection.
- Failure/retry behavior when Jev, Showdown, or the WebSocket is unavailable.

---

### Task 1: Repository and environment preflight

**Files:**
- Inspect: `pyproject.toml`, `README.md`, `.env*`, `docs/research/phase-0-jev-opencode.md`
- Update: `docs/validation/2026-09-20-e2e-demo-validation.md`
- Update: `docs/validation/2026-09-20-e2e-demo-validation-todo.md`

- [ ] Verify current Git state, Python executable, dependency lock, environment variables by name only, startup command, and existing test baseline.
- [ ] Verify Jev configuration resolves to the documented OpenCode route without printing secrets.
- [ ] Record exact commands, versions, and preflight results in the assessment document.

### Task 2: Backend and Jev live-path smoke validation

**Files:**
- Inspect: `src/jev_showdown/decision/opencode_jev.py`, `src/jev_showdown/agent.py`, `src/jev_showdown/main.py`, `src/jev_showdown/web/server.py`
- Test: existing unit tests plus a live Jev request through the application path.
- Update: assessment and TODO documents only unless a defect is found.

- [ ] Start the dashboard with the project-local interpreter and capture startup logs.
- [ ] Confirm the application exposes the expected HTTP/WebSocket routes.
- [ ] Exercise one actual Jev decision path and verify request shape, typed response, criteria, latency, usage/cost, redacted telemetry, and no secret leakage.
- [ ] If a defect is found, reproduce it with a focused test before changing implementation, then rerun the focused and full tests.

### Task 3: Real Showdown battle validation

**Files:**
- Inspect: `src/jev_showdown/battle/`, `src/jev_showdown/main.py`, `.env*`
- Update: assessment and TODO documents with battle evidence.

- [ ] Start a real Gen 9 Random Battle using configured credentials/public matchmaking.
- [ ] Correlate Showdown protocol events with backend logs and dashboard updates for at least multiple turns.
- [ ] Verify legal move/switch/tera handling, fallback behavior if needed, turn timer behavior, and battle-end cleanup.
- [ ] Record opponent type and matchmaking limitations honestly; do not claim a difficult bot unless Showdown actually provided one.

### Task 4: Playwright visual and interaction audit

**Files:**
- Inspect: `src/jev_showdown/web/static/index.html`, `src/jev_showdown/web/static/style.css`, `src/jev_showdown/web/static/app.js`
- Create: screenshots outside the repository or in the validation output directory.
- Update: assessment document with visual findings and screenshot paths.

- [ ] Inspect the idle, matchmaking, active-turn, inspector-expanded, fallback/error, observed-result, and reset states with Playwright snapshots and screenshots.
- [ ] Use human visual review of the rendered dashboard at the intended recording viewport and one narrow viewport.
- [ ] Verify Pokémon assets, battle stage, team rows, fog-of-war, Jev input/output, validation, act, and observed result are visually understandable.
- [ ] Check browser console errors/warnings, failed network requests, WebSocket stability, and accessibility-critical text visibility.
- [ ] If a visual or interaction defect materially harms the demo, add a focused regression check, implement the smallest fix, and retest visually.

### Task 5: Reliability and failure-path validation

**Files:**
- Inspect: server logs, browser console/network logs, relevant tests.
- Update: assessment and TODO documents.

- [ ] Test retry after battle end, WebSocket disconnect/reconnect behavior, Jev timeout/error fallback, and clean shutdown.
- [ ] Confirm no stale local project process remains after the run.
- [ ] Run the complete test suite, compile check, lock check, and diff check after any fixes.

### Task 6: Final demo-readiness assessment

**Files:**
- Update: `docs/validation/2026-09-20-e2e-demo-validation.md`
- Update: `docs/validation/2026-09-20-e2e-demo-validation-todo.md`

- [ ] Mark each rubric item Pass, Conditional, or Fail with evidence.
- [ ] List remaining limitations separately from actual defects.
- [ ] State whether the project is ready for a real recording, with the exact startup command and any required account/network caveats.
- [ ] Recheck Git status and report whether validation changes are committed or remain uncommitted.
