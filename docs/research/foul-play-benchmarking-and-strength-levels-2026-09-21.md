# Foul Play Benchmarking and Strength Levels

**Date:** 2026-09-21  
**Project:** `pokemon-showdown-jev-agent`
**Purpose:** Explain how to use Foul Play as an existing Pokémon Showdown bot benchmark without assuming it has official difficulty levels.

## Direct answer

Foul Play does not appear to provide named difficulty levels such as Easy, Medium, or Hard.

Its strength is controlled by search-budget configuration, mainly:

- `--search-time-ms`
- `--search-parallelism`
- `--search-threads`
- team-preview search-time and parallelism settings

The current configuration defines a default search time of approximately 100 ms, one parallel search, and one search thread. These are configuration values, not official difficulty modes.

Source: [Foul Play configuration](https://github.com/pmariglia/foul-play/blob/main/fp/config.py)

## What this means for our testing

If we run Foul Play with its default configuration, we fight its default configured search strength. We are not automatically fighting the strongest version associated with its best published ladder result.

More search time or parallelism generally gives the bot more opportunity to evaluate positions, but it does not guarantee a proportional increase in playing strength. The exact result depends on hardware, format, search behavior, and the current repository version.

Therefore, we should describe the opponent precisely in test results:

```text
Foul Play commit/version
Pokémon Showdown commit/version
format
search time
search parallelism
search threads
number of games
```

## Practical benchmark tiers

These are our testing tiers, not official Foul Play levels:

| Tier | Configuration idea | Purpose |
|---|---|---|
| Basic | Small search budget | Confirm Jev can beat a weak search opponent |
| Default | Foul Play’s default settings | Establish a reproducible baseline |
| Strong | Larger search budget and/or more threads | Test against a stronger configured opponent |
| Maximum practical | Highest budget supported by the local machine | Stress test before online evaluation |

The exact numerical values should be chosen after measuring local runtime. We should not increase the search budget so much that the opponent itself times out or behaves differently from a normal battle agent.

## Recommended evaluation order

Use the official Pokémon Showdown engine running locally as the referee. Foul Play is the opponent; it should not be treated as the authoritative battle simulator.

Recommended progression:

1. `poke-env` `SimpleHeuristicsPlayer`
2. Foul Play with a small search budget
3. Foul Play with its default configuration
4. Foul Play with a larger search budget
5. An optional additional strong open-source bot, such as Laplace, if its current build is reproducible and supports the exact format
6. Real online ladder games against human players

The first levels are gates. If Jev cannot reliably beat a basic local baseline, we should not spend money on a large Foul Play series or online ladder games.

## Foul Play compatibility and limitations

Foul Play’s README documents single-battle support and gives an example using `gen9randombattle`. It uses `poke-engine` to search through battles.

Source: [Foul Play repository](https://github.com/pmariglia/foul-play)

The Foul Play README also states that some mechanics are unsupported, and `poke-engine` explicitly warns that it is not as complete or robust as the official Pokémon Showdown battle engine.

Sources:

- [Foul Play README](https://github.com/pmariglia/foul-play)
- [poke-engine README](https://github.com/pmariglia/poke-engine)

This creates an important separation:

```text
Official local Pokémon Showdown = battle referee
Foul Play = benchmark opponent
Our harness = Jev player being evaluated
```

If Foul Play and the official simulator disagree, the official Showdown result is authoritative.

Before treating Foul Play as a serious Gen 9 Random Battle benchmark, run a compatibility smoke test to confirm that its current branch handles the project’s format and important mechanics correctly.

## Cost-conscious Jev testing

Because Jev calls cost money, testing should be staged.

### Stage 1: no Jev calls

Use the local Showdown server to test:

- battle-state construction;
- legal action generation;
- move and switch serialization;
- visible and hidden opponent information;
- damage and status facts;
- stale-response protection;
- fallback speed; and
- total context-construction latency.

### Stage 2: small Jev decision audit

Send a small set of recorded battle states to Jev rather than playing complete matches. Include attack-versus-switch, setup, hidden-opponent, double-switch, and endgame positions.

This validates whether Jev understands the harness translation before paying for full matches.

### Stage 3: local Jev matches

Run a small sequential batch against `SimpleHeuristicsPlayer`, then Foul Play. Expand the batch only if:

- no illegal actions occur;
- no stale decisions are submitted;
- latency stays within the battle budget;
- Jev responses are valid; and
- the cost per battle is acceptable.

### Stage 4: online validation

Only after the local gates pass should we use the public ladder to measure Elo against humans. Freeze the harness, Jev model, prompt/schema, Showdown version, and benchmark configuration before starting.

Public ladder automation should also be checked against current Pokémon Showdown policy. Technical support for laddering does not automatically establish permission for every automated use.

## Metrics to record

For every benchmark series, record:

- opponent bot and version/commit;
- Showdown version/commit;
- format;
- Foul Play search settings;
- number of battles;
- wins, losses, and draws;
- Jev calls per battle;
- Jev cost per battle;
- average, p95, and p99 decision latency;
- timeout count;
- fallback count;
- illegal-action count;
- stale-response count;
- battle duration; and
- replay files.

For online play, also record:

- starting and ending rating;
- opponent rating distribution;
- GXE or equivalent performance metric if available;
- total games; and
- whether the result is a temporary peak or a stable result over a meaningful sample.

## Important interpretation rule

A local win against Foul Play does not directly equal a particular Elo. It tells us that Jev beat one configured bot under one engine, version, and search budget.

A real online ladder run is required to measure human-ladder Elo. Even then, a small number of games or a temporary peak is not enough to claim professional-level performance.

## Final recommendation

Do not assume we are directly fighting Foul Play at its maximum strength. Start with its default configuration, then increase the search budget in controlled tiers. Use the official local Showdown engine as the referee, spend Jev money only after no-cost correctness checks pass, and reserve online ladder games for the final frozen evaluation.
