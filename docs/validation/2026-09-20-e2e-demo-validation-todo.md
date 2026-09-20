# End-to-End Demo Validation TODO

This is the execution ledger for the fresh real-runtime validation. It replaces the unavailable `todowrite` integration with a repository-local checklist.

- [x] Preflight repository, `.venv`, uv lock, configuration names, and documented Jev route.
- [x] Run the existing test baseline before live testing.
- [x] Start the backend with the project-local Python and capture logs.
- [x] Verify live Jev/OpenCode request and typed response through the application path.
- [x] Start a real Pokémon Showdown Gen 9 Random Battle.
- [x] Correlate Showdown events, backend logs, WebSocket traffic, and rendered dashboard state.
- [x] Inspect idle, active, inspector, fallback, result, and reset dashboard states with Playwright.
- [x] Visually review the dashboard screenshots for mixed technical/non-technical audiences.
- [x] Evaluate Pokémon assets and replace the prior sprite source with official Showdown assets plus a safe fallback.
- [x] Check browser console, network, WebSocket, backend exceptions, and orphaned processes.
- [x] Exercise Jev failure/fallback and battle retry paths.
- [x] Fix and retest material defects using focused regression tests.
- [x] Run the full post-validation verification suite.
- [x] Complete the assessment rubric and state demo readiness honestly.

Result: `DEMO READY — VERIFIED FOR LOCAL RECORDING`. See the assessment markdown for evidence and limitations.
