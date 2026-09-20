# Dashboard Codex handoff

The dashboard visual direction has been deliberately reset. The previous
dashboard and its visual guidance were retired because they produced a similar
low-quality result more than once.

Read first:

1. [Dashboard product contract](dashboard-product-contract.md)
2. `docs/research/phase-0-jev-opencode.md`
3. `docs/research/phase-1-research-and-architecture.md`
4. The current implementation under `src/agent/`, `src/decision/`, and
   `src/dashboard/`

The product contract is the only dashboard authority. It defines the real
Showdown → harness → Jev → validation → order → observed-result behavior and
the evidence the interface must expose. It deliberately leaves the visual
solution open.

Preserve the working real-battle path, protocol stream, official Showdown
renderer integration, decision adapter, validation, telemetry origin, and
fallback behavior unless inspection finds a concrete defect. Do not add a
second battle client, duplicate game-state UI, fabricated Jev reasoning, manual
move controls, or marketing copy.

The next implementation agent is expected to create an original visual
solution. Do not treat deleted plans, mockups, screenshots, or validation
records as design references. Verify the result on a normal desktop/laptop
landscape viewport with Playwright and inspect screenshots as a human viewer.
