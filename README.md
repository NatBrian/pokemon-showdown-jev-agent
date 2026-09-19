# Autonomous Pokémon Showdown Agent Powered by Jev AI

This repository will contain the Generation 9 Random Battles agent, its Showdown harness, Jev decision adapter, and benchmark tooling.

## Current status

Phase 0 is complete for Jev/OpenCode connectivity. No game-playing code has been implemented yet.

The verified integration finding is recorded in [the Phase 0 research log](docs/research/phase-0-jev-opencode.md).

## Planned phases

1. Research, analysis, and architecture proposal.
2. Harness and autonomous battle implementation.
3. Baseline benchmarking and optimization.

## Important constraint

Jev is a typed decision model. The agent should call its decision endpoint directly and should not send Jev requests through OpenCode's normal chat/agent loop.
