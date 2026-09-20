# Project alignment

Status: concise project context. The dashboard rules live in
[the dashboard product contract](design/dashboard-product-contract.md).

## Purpose

This project is an autonomous Pokémon Showdown Gen 9 Random Battles agent
powered by Jev AI. The showcase must let a technical or non-technical viewer
observe Jev making decisions in a real game, understand the evidence supplied
to Jev, see the typed decision that comes back, and see the legal action and
result reach Showdown.

The product should be cloneable and runnable locally. The primary environment is
the owner's Windows PC; paid hosting, a database, cloud infrastructure, and a
large frontend framework are not required for the MVP.

## Audience

The default experience should be understandable to a general technology
audience. A deliberate inspection path should support engineers who want the
structured state, deterministic facts, request, response, validation, order,
and protocol evidence. The interface should demonstrate the system rather than
make comparative marketing claims.

## Scope

- Focus on Jev; do not add Claude, GPT, Gemini, or another comparison agent.
- Use the real Showdown server and Gen 9 Random Battle format, not a simplified
  combat imitation.
- Use `poke-env` for the initial battle connection and legal-order interface.
- Keep one active battle in the first product.
- Keep credentials in local `.env` configuration and never expose them in the
  dashboard or logs.
- Do not create competing bots for the initial project. Existing local
  `poke-env` reference players may be used for repeatable checks.

## Runtime path

The local user journey is:

1. Clone the repository and install dependencies.
2. Run the project and open the local dashboard.
3. Start the autonomous battle.
4. Connect/authenticate with Showdown and search the fixed Gen 9 Random Battle
   format.
5. Observe the agent receive state, ask Jev, validate a choice, submit an
   order, and continue until the battle ends.

Startup must represent the actual application states, including connection,
authentication, format selection, matchmaking, battle initialization, active
play, cancellation, and failure. A preloaded animation is not acceptable.

## Harness boundary

The application boundary is:

`Showdown → poke-env → deterministic evaluator → Jev → validator → Showdown`

`poke-env` supplies real public battle state and legal orders. The application
may calculate legal candidate actions, type effectiveness, damage ranges or
estimates, priority/speed facts when knowable, field consequences, switch
safety, and Terastallization legality. Unknown opponent data and calculator
assumptions must remain explicit.

Jev chooses among the legal, annotated candidates. Jev is not asked to parse raw
protocol, reproduce the game rules, or invent a Showdown command. The adapter
maps the typed choice to a legal `BattleOrder`, validates it, submits it, and
uses a legal fallback when provider or validation failure requires one.

## Evaluation

Public matchmaking demonstrates operation against a real opponent. It is not a
fixed difficulty ladder. Repeatable local checks may use existing
`poke-env` players such as `RandomPlayer`, `MaxBasePowerPlayer`, and
`SimpleHeuristicsPlayer`. Meaningful performance claims require multiple
battles and should report win rate, uncertainty, latency, fallback rate, and
illegal-action rate rather than relying on one lucky game.

Human challenges are optional qualitative evidence, not the controlled bot
benchmark. A single human match does not establish human-level strength.

## Resolved product decisions

- The dashboard is an observer, not a second human controller.
- Viewers do not manually choose moves, switches, or settings.
- Fallbacks are allowed for reliability but must be unmistakably attributed to
  the adapter, never to Jev.
- No built-in recording, elaborate replay workflow, or production hosting is
  required for the MVP.
- The dashboard must show behavior and evidence instead of slogans or
  comparative claims.

For dashboard-specific behavior, source-of-truth rules, and creative freedom,
use [dashboard-product-contract.md](design/dashboard-product-contract.md).

## Related research

- [Phase 0 Jev/OpenCode research](research/phase-0-jev-opencode.md)
- [Phase 1 research and architecture](research/phase-1-research-and-architecture.md)
