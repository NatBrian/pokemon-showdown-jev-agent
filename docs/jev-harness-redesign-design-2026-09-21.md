# Jev Pokémon Harness and Decision-System Redesign

**Date:** 2026-09-21  
**Project:** `autonomous-pokemon-showdown-jev-agent`  
**Target format:** Gen 9 Random Battle singles (`gen9randombattle`)  
**Status:** Updated design choice after source-level study of Foul Play and PokéChamp; no implementation included

## Executive design choice

The recommended redesign is a **truth-first, thin, latency-bounded hybrid harness**.

The harness should do four things extremely well:

1. Represent the real Showdown state accurately.
2. Calculate or expose only verified mechanical facts.
3. Represent unknown information as uncertainty instead of invented facts.
4. Give Jev a compact, self-describing set of legal choices and consequences.

Jev should remain responsible for the strategic decision. The harness should not become a large hand-coded Pokémon strategy engine that tells Jev which action is best.

The central boundary is:

```text
Showdown / poke-env
    ↓
Verified battle truth
    ↓
Legal actions + mechanical consequences
    ↓
Unknown-information beliefs
    ↓
Compact neutral decision context
    ↓
One Jev decision
    ↓
Fast legality and freshness validation
    ↓
Showdown order
```

## Decision after studying Foul Play and PokéChamp

This redesign is **not obsolete**. Its truth-first harness boundary remains the correct foundation. However, it is incomplete if interpreted as only a live prompt adapter. Foul Play and PokéChamp show that a competitive system needs two coordinated planes:

```text
Live decision plane:
Showdown truth -> verified context -> Jev choice -> legality gate -> order

Offline/shadow evaluation plane:
replays -> trusted mechanics oracle -> possible-world scenarios -> benchmarks -> measured improvements
```

The recommended action is a **targeted rework, not a rewrite from scratch**:

- Preserve the existing Showdown/poke-env connection and Jev integration where they are operationally sound.
- Rework the state, action, consequence, uncertainty, and validation boundaries so they support all legal moves and switches without misleading Jev.
- Add an offline/shadow evaluation subsystem. It is required to determine whether Jev is improving, whether a harness feature is wrong, and whether the agent can compete with strong bots.
- Add a bounded opponent-world and response model. Borrow Foul Play's evidence and possible-world discipline, but do not place unbounded MCTS in the live path.
- Add PokéChamp-style semantic translation only after the underlying values are labelled as observed, calculated, inferred, or unknown.

The goal is not to copy either bot. Foul Play already owns the full-search approach, and PokéChamp already owns the repeated-LLM-prompt approach. Our differentiator should be a trustworthy, low-latency decision interface in which Jev remains the strategic policy while the system supplies the information and safety infrastructure that Jev cannot obtain by itself.

### What the bot study changes

The previous design already specified canonical state, legal actions, uncertainty, semantic consequences, freshness checks, and fallback. The study adds four explicit requirements:

1. **A mechanics-oracle boundary.** Any local simulator or calculator must be differentially tested against Showdown before its output can influence Jev. A fast approximate simulator may be useful for offline hypotheses, but it cannot be the referee.
2. **A possible-world boundary.** Hidden opponent information should be represented as multiple evidence-weighted possibilities, not one guessed set and not only a generic "unknown." Live Jev input may contain a bounded summary; offline evaluation may sample more worlds.
3. **A response-consequence boundary.** For each of our legal actions, compile the important opponent stay, move, setup, status, and switch responses. This is a one-turn consequence view, not a hand-coded final answer.
4. **An evaluation boundary.** Record replayable decision packages and separate harness errors, mechanics errors, Jev errors, timeout errors, and opponent-strength effects. Win rate alone cannot tell us which subsystem needs repair.

### What we should not copy

- Do not port Foul Play's full MCTS and hand-coded evaluation into the live path before proving that Jev needs it.
- Do not use PokéChamp's approximate `LocalSim` as authoritative battle truth.
- Do not make a Bayesian prediction look like a confirmed move, item, ability, or teammate.
- Do not add several serial Jev calls, an LLM debate loop, or a large prompt because the other bot uses one.
- Do not replace Jev with a hard-coded score that always prefers damage, type advantage, or the action selected by a local simulator.

This design directly addresses the three project constraints:

- **Wrong information:** every fact has a source, unit, and confidence; uncertain or unavailable facts are not presented as certain.
- **Overfitting:** the harness does not prune legal actions or hard-code a large Pokémon playbook; it exposes consequences and lets Jev choose.
- **Latency:** the live path uses one compact Jev request, bounded computation, caching, and an immediate deterministic fallback.

## What this redesign is not

This is not a plan to:

- write a complete Pokémon AI in hand-coded rules;
- replace Jev with a simple heuristic scorer;
- predict every opponent action with a giant rule tree;
- support VGC, singles, Random Battle, and every Showdown format at once;
- build a full multi-turn search system before the state and mechanics are trustworthy; or
- guarantee that the resulting agent always defeats professional players.

The first target remains Gen 9 Random Battle singles. Other formats should later use format-specific adapters rather than silently sharing assumptions.

## Current-system problems this design addresses

The current harness already has a useful foundation: `poke-env` connects to Showdown, parses battle requests, creates orders, Jev selects a candidate ID, and the validator sends the stored `BattleOrder`.

The important weaknesses are at the information boundary:

- The candidate builder can drift from the actual legal orders.
- Exact damage values and heuristic estimates use incompatible units.
- A heuristic estimate can be presented as if it were a damage percentage.
- Jev receives little recent history.
- Unknown opponent information is represented, but not as a useful belief model.
- Request metadata such as `rqid`, forced-switch state, and waiting state is not fully represented in the decision snapshot.
- The prompt asks for the “strongest legal action,” which encourages immediate damage rather than overall winning position.
- The fallback is mostly `base_power × type_multiplier`, which is not a sufficient Pokémon strategy.
- The local WebSocket test server tests orchestration, not Pokémon mechanics.
- Telemetry observes protocol events but is not connected to a replayable strategic decision package.

The redesign should fix the information and correctness boundary before adding sophisticated strategy features.

## Design principles

### Principle 1: Showdown is authoritative

The real Showdown battle engine is the final authority for legality and outcomes. `poke-env` is the primary protocol and battle-object adapter.

The project should not silently override Showdown with an approximate Python interpretation. Any local calculation must be labelled as one of:

- exact and verified;
- bounded or ranged;
- inferred from observations; or
- unavailable.

### Principle 2: Unknown is a valid value

The harness must never turn missing information into a confident guess.

Examples:

- An unrevealed move is not “probably Earthquake” unless the belief model gives evidence and a probability.
- Unknown item is not serialized as a default item.
- Incomplete stats do not become a fake precise damage percentage.
- An opponent’s hidden Pokémon is not treated as absent.

### Principle 3: Facts before strategy

The first live redesign should focus on accurate facts and neutral consequences. It should not contain a large collection of rules such as “always switch to a counter” or “always use setup when the opponent switches.”

The harness may expose mechanically proven signals, such as:

- this action is legal;
- this move cannot KO;
- this move has a guaranteed KO under the known state;
- this switch has a known hazard cost;
- this Pokémon is the only known survivor against a specific attack.

It should not initially produce unverified conclusions such as “this is definitely our win condition” or “the opponent will certainly switch.” Those can be hypotheses, not facts.

### Principle 4: Never remove Jev’s decision space without evidence

The harness should present all meaningful legal actions. It should annotate actions, not preselect a winner.

If five actions are legal and strategically meaningful, Jev should see all five. The harness must not remove an action merely because a local heuristic thinks it is inferior.

The only permitted removal is mechanical illegality or an action that Showdown itself cannot accept.

### Principle 5: One live Jev decision per request

Multiple sequential Jev calls would increase latency and create a hand-coded debate system around Jev. The initial live design should make one compact decision request per battle request.

Additional Jev questions may exist in offline evaluation or shadow mode, but they should not block the live order unless their latency has been measured and justified.

## Recommended architecture

The system is larger than the live harness, but the live harness remains the only component allowed to block a battle order. Split the design into two planes with a strict boundary:

### Live decision plane

This plane runs on every Showdown request:

```text
Showdown/poke-env
  -> canonical reducer and fact ledger
  -> legal action registry
  -> cached verified mechanics
  -> bounded belief/response compiler
  -> compact Jev Choice context
  -> Jev policy gateway
  -> freshness and legality gate
  -> Showdown order or deterministic fallback
```

Its job is to make one high-quality decision within the timer. It must not run an unbounded search, repeatedly ask Jev to debate itself, or depend on a prediction that has not been validated.

### Offline and shadow evaluation plane

This plane can spend more time because it does not control the live timer:

```text
Showdown replays / recorded decision packages
  -> exact or differentially tested mechanics oracle
  -> evidence-weighted possible worlds
  -> optional bounded simulator/search adapter
  -> Jev replay decisions and reference-bot decisions
  -> ablation, calibration, latency, and outcome analysis
```

It is where Foul Play-style world sampling, optional `poke-engine` comparison, deeper counterfactuals, and expensive Jev experiments belong first. A feature may move from shadow to live only after its correctness, latency, and strategic-bias effects are measured. This prevents the live harness from becoming a hidden second bot while still giving the project a path to use search if Jev-only decisions are not competitive.

### 1. Battle truth core

Create a canonical internal state assembled from `poke-env` and the current Showdown request.

It must include:

- battle ID;
- format;
- turn number;
- state version;
- request ID / `rqid`;
- request type;
- `forceSwitch`, `wait`, `trapped`, and `maybeTrapped` information;
- timer/deadline information;
- active Pokémon;
- own team state;
- revealed opponent state;
- unknown opponent slots;
- moves, PP, and disabled status;
- weather, terrain, fields, hazards, and side conditions;
- Tera availability; and
- legal actions.

Every field should carry provenance:

```text
observed   = directly supplied by Showdown or poke-env
calculated = deterministically derived from observed facts
inferred   = a hypothesis with evidence and confidence
unknown    = unavailable and intentionally not guessed
```

The canonical state is the only state from which decision context should be built. Telemetry scanners should not independently become a second source of truth.

### 2. Legal action registry

Build a registry of actions from the actual current legal request.

Each action should contain:

- stable action ID;
- action kind: move, Tera move, switch, or other legal order;
- target, when relevant;
- stored real `BattleOrder`;
- required PP or once-per-battle resource;
- immediate mechanical effect;
- outcome facts;
- uncertainty fields; and
- a neutral human-readable description.

The registry should derive from, or be reconciled against, `battle.valid_orders`. The project must not maintain a separate imagined action universe.

The Jev-facing action list should be a projection of this registry. The validator should use the same registry to map Jev’s ID back to the original order.

#### Our move actions and our switch actions are different decisions

The harness must not treat a switch as a move with a different label. Jev needs to understand the strategic meaning of both choices.

For an own move action, provide:

- move name and category;
- target;
- direct effect;
- damage range and KO probability when calculable;
- accuracy and priority;
- status or stat-stage effect;
- field or hazard effect;
- PP cost;
- Tera usage, if applicable; and
- what the action allows or risks on the next turn.

For an own switch action, provide:

- the incoming Pokémon;
- current HP and status of the incoming Pokémon;
- types, ability, item, and known moves;
- entry-hazard damage and other switch-in effects;
- survival probability against the opponent’s possible responses;
- whether the incoming Pokémon threatens the opponent;
- whether it creates a favorable next-turn action;
- what important resource is preserved by switching; and
- what coverage, status, setup, or double-switch risk is accepted.

The switch description must not simply say “Switch to X; favorable matchup.” It should explain why the matchup is favorable and what could invalidate the switch. If those facts cannot be calculated reliably, the field must be marked uncertain rather than asserted.

The final Jev Choice must contain both move candidates and switch candidates whenever both are legal. The harness must not pre-decide that attacking is the real decision and switching is only a fallback.

### 3. Verified mechanics compiler

The mechanics compiler should calculate action consequences where the required information is available.

For each action, use separate fields for:

- damage minimum and maximum;
- damage unit;
- KO probability;
- survival probability;
- move accuracy;
- priority;
- speed-order result;
- status chance;
- stat-stage change;
- field or hazard effect;
- switch-in damage;
- resource cost; and
- calculation assumptions.

If exact calculation is not possible, do not manufacture a precise percentage. Return a range, an explicit unknown, or a separately named rough utility estimate.

The following rule is mandatory:

> A heuristic number must never be labelled as exact damage, a damage percentage, a KO probability, or a win probability.

For the initial redesign, it is better to provide fewer correct facts than many incorrect facts.

### Mechanics oracle and optional simulator adapter

Foul Play demonstrates the value of a fast simulator, while PokéChamp demonstrates the danger of relying on an approximate one. The project should therefore define three levels of mechanical output:

1. **Showdown-authoritative:** directly observed protocol facts and outcomes accepted by the real battle server.
2. **Verified local calculation:** deterministic output from a calculator or simulator that has passed differential fixtures against Showdown for the supported format and mechanic.
3. **Unverified estimate:** a hypothesis used only in offline experiments and never presented to Jev as an exact fact.

An optional `poke-engine` adapter may be evaluated as a speed and scenario tool, but it must remain behind this boundary. It is not automatically authoritative merely because it is fast or used by Foul Play. Before live use, it needs differential tests for damage rolls, abilities, items, hazards, statuses, switching, Terastallization, and edge cases relevant to Gen 9 Random Battle. If parity is incomplete, the adapter can still support shadow comparison and offline search while its results remain labelled accordingly.

The mechanics layer should expose both its result and its assumptions. A Jev-facing result must never hide whether it came from Showdown observation, a verified calculation, a sampled world, or an estimate.

### 4. Hidden-information ledger

Random Battle requires uncertainty tracking, but this must not become speculative storytelling.

For each revealed opponent Pokémon, the ledger may track candidate:

- moves;
- ability;
- item;
- Tera type;
- speed range;
- offensive/defensive role; and
- possible set family.

Every hypothesis must include:

- evidence source;
- confidence or probability;
- last update turn; and
- mechanical consequences if true.

The ledger should begin with known format/set-generation information where available, then update from observed moves, damage, status, and switching behavior.

The ledger should not directly choose the Jev action. It supplies uncertainty that Jev can consider.

### Possible-world compiler

The belief ledger is the durable record; the possible-world compiler is the bounded decision-time projection of that record. It should:

- eliminate worlds contradicted by observed moves, damage, speed, items, abilities, fainting, or team composition;
- retain several plausible worlds when evidence does not identify one set;
- attach probability, confidence, or an explicit non-probabilistic uncertainty label to every retained hypothesis;
- aggregate only when the aggregation preserves important threats, immunities, sweepers, walls, and revenge-kill possibilities; and
- use a deterministic seed or recorded sample set so a decision can be replayed.

For live play, the compiler should summarize the highest-impact worlds and an explicit residual unknown bucket. For offline evaluation, it may sample more worlds and compare Jev's action across them. This gives us Foul Play's hidden-information discipline without forcing the live harness to run full MCTS.

### Opponent team ledger and fog of war

The opponent must be represented as a six-slot team ledger, not only as the currently active Pokémon.

Each opponent slot should have an explicit visibility state:

```text
unknown_slot       = the slot exists, but no species has been revealed
revealed_bench     = species is known and currently inactive
revealed_active    = species is known and currently active
fainted            = the slot is known and no longer able to act
```

For a revealed opponent Pokémon, retain information after it switches out:

- species and forme;
- current and maximum known HP or HP range;
- status;
- revealed moves and PP evidence;
- revealed ability;
- revealed item evidence;
- Tera status and Tera type if revealed;
- boosts, drops, effects, and hazards relevant to it;
- last seen turn; and
- possible unrevealed set details with confidence.

For an unknown slot, do not invent a species or set. Instead provide:

- that an unknown slot exists;
- how many unknown slots remain;
- the possible role or threat categories supported by the Random Battle distribution;
- the evidence that has ruled out any possibilities; and
- the remaining uncertainty mass.

This distinction is important:

- a Pokémon that is currently off the field is not the same as an unknown Pokémon;
- a revealed species with unknown moves is not the same as a fully known set; and
- a fainted Pokémon is not a possible future switch.

The Jev state should preserve these distinctions explicitly.

### Opponent action model: the enemy’s possible movement

“Enemy movement” means the opponent’s possible action on the current turn. The harness must model both opponent moves and opponent switches.

For the active opponent Pokémon, represent possible response categories:

- known or hypothesized attack;
- status move;
- setup or stat-changing move;
- recovery or protection move;
- field, hazard, or speed-control move;
- Terastallization plus a move, when available;
- switch to each revealed bench Pokémon; and
- switch to an unknown slot represented as an uncertainty bucket.

The harness must not claim that the opponent will choose one response. It should provide a bounded response distribution:

- response ID or response category;
- probability or confidence, when evidence supports one;
- source of the estimate;
- exactness of the response’s mechanics; and
- the remaining unknown-response mass.

For a revealed opponent move, use the real move semantics and calculate its effects. For an unrevealed move, use a clearly labelled hypothesis or a broader effect category. Do not fabricate a specific hidden move merely to make the decision easier.

For an opponent switch, calculate the consequence separately for:

- each revealed possible incoming Pokémon; and
- an aggregated unknown-opponent bucket when the species is not known.

The unknown bucket must remain meaningful. It must not be treated as an average Pokémon that hides the possibility of a dangerous sweeper, wall, immunity, or revenge killer.

### Action-response consequences

For each of our meaningful legal actions, the decision context should expose a shallow action-response view:

```text
our_action
    → opponent stays and attacks
    → opponent stays and sets up/statuses
    → opponent switches to revealed Pokémon
    → opponent switches to unknown slot
    → resulting state and resource changes
```

This is not a full multi-turn search tree. It is a bounded, one-turn counterfactual summary that lets Jev compare “attack” versus “switch” while seeing that the opponent can also move or switch.

Each response outcome should include:

- damage and status changes;
- whether either side is KO’d;
- resulting active Pokémon;
- remaining legal options;
- resource changes;
- information revealed; and
- whether the outcome helps or harms the known winning plans.

The harness should not collapse all response outcomes into one hand-coded score. Jev should see the important branches and their uncertainty.

For latency, the live context can include exact branches for revealed high-probability responses and aggregated buckets for low-confidence or unknown responses. The aggregate must retain its probability mass and uncertainty label.

### Strategic hypothesis layer: plans without hard-coded answers

The harness still needs to represent expert concepts such as win condition, lose condition, progress, resource value, and risk. Omitting them entirely would leave Jev with mechanics but not enough strategic meaning. The safe solution is to represent them as **evidence-backed hypotheses**, not as authoritative conclusions.

For each plausible plan, provide:

- plan type;
- evidence supporting it;
- required steps;
- Pokémon and resources it depends on;
- known opponent answers;
- what would invalidate it; and
- confidence or uncertainty.

Possible plan types for Random Battle include:

- immediate KO or revenge-kill plan;
- setup-and-sweep plan;
- hazard/status attrition plan;
- defensive outlast plan;
- preserve-a-check plan;
- pivot-to-win-condition plan; and
- necessary sacrifice or high-risk recovery plan.

The harness should expose more than one plausible plan when more than one exists. It must not label one plan as the answer merely because a local rule prefers it. Jev should decide which plan matters most.

Likewise, a lose-condition hypothesis should state the concrete threat sequence:

- immediate KO;
- opponent setup followed by a sweep;
- loss of the only answer to a revealed threat;
- inability to break a defensive Pokémon;
- dangerous unrevealed switch; or
- resource exhaustion.

The goal is to tell Jev what can go wrong and why, without telling Jev which response to select.

The context should also include a position-classification hypothesis:

- opening or information-gathering position;
- stable position where safe progress is preferred;
- setup opportunity;
- endgame or cleanup position; or
- emergency position where the normal safe line is already losing.

The classification must include evidence and confidence. It is a compact summary of the state, not a hard-coded policy. Jev should be able to reject it when the supplied action consequences indicate a different plan.

Threats should be represented similarly. For each important opponent threat, provide:

- threat identity or category;
- immediate and future danger;
- evidence;
- likely counterplay;
- which of our resources answer it; and
- what happens if we ignore it this turn.

### Resource and progress ledger

Expert players value resources that are not visible in a single damage calculation. The decision context should track:

- current HP and HP ranges;
- number of healthy Pokémon on each side;
- recovery and important offensive PP;
- status conditions;
- boosts and drops;
- Tera availability;
- remaining checks, pivots, and revenge killers;
- revealed information already obtained; and
- safe future switch options.

Resource criticality must be labelled as a hypothesis with evidence. For example:

```text
resource: Rotom-Wash
role_hypothesis: only known safe switch into revealed physical attacker
evidence: survives listed attacks and threatens burn or KO
criticality: high, confidence 0.78
```

For each action, expose progress channels rather than one overall hand-coded score:

- direct damage;
- KO pressure;
- status pressure;
- hazard pressure;
- speed control;
- setup progress;
- safe entry created;
- information gained;
- opponent options removed; and
- resources spent or preserved.

Jev can then compare an attack, switch, setup, status, or sacrifice without the harness deciding that damage is always the most important form of progress.

### Risk, reward, and continuation

The action-response view should explicitly contain:

- best-case result;
- likely-case result;
- worst-case result;
- catastrophic failure condition;
- whether the position can recover after failure;
- what the action enables next turn; and
- what the opponent can do next turn.

This lets Jev distinguish a bad gamble from a necessary gamble. The harness should not produce a single “risk score” that replaces Jev’s judgment.

The live path should provide a bounded continuation summary rather than a full search tree:

```text
our action
    → opponent response
    → resulting state
    → important next-turn options
```

For high-confidence branches, include the next-turn legal affordances. For unknown branches, preserve an uncertainty bucket. Longer two- or three-turn search can be added later in offline evaluation, but it should not be required for the first latency-bounded live design.

### Information gain and double-switch reasoning

The history layer must record evidence that expert players use to update beliefs:

- revealed moves;
- damage received and dealt;
- item and ability reveals;
- switching patterns;
- repeated staying in or switching out;
- previous setup attempts;
- status and hazard interactions; and
- Tera usage.

Each action should state what it may reveal. For example, a switch may reveal which opponent Pokémon is being preserved, while a safe scouting move may reveal an item, ability, speed relationship, or coverage move.

The response matrix must also include the double-switch case: our Pokémon switches while the opponent switches to a different revealed or unknown Pokémon. The result should show whether our switch gains a favorable matchup or accidentally gives the opponent a free attacker.

### 5. Neutral decision context

The Jev state should be compact and self-describing. It should contain:

- format rules and a short glossary of Pokémon terms;
- canonical observed state;
- verified mechanical facts;
- hidden-information hypotheses;
- complete six-slot opponent ledger with visible, inactive, fainted, and unknown slots distinguished;
- possible opponent moves and switches, including an unknown-response bucket;
- shallow action-response consequences for our move and switch candidates;
- evidence-backed candidate win plans and lose-condition hypotheses;
- resource criticality and progress channels;
- best-case, likely-case, worst-case, and recovery consequences;
- relevant history and information each action may reveal; and
- all legal actions;
- candidate consequences; and
- decision deadline.

The glossary should define terms that cannot safely be assumed, such as:

- switch;
- setup;
- status;
- hazard;
- priority;
- counter/check;
- safe action;
- risky prediction; and
- win/lose condition.

The definitions should be short and generic. They should explain meaning without telling Jev which action to choose.

The context should not contain a hard-coded action score or a statement such as “action 3 is best.”

### 6. Jev policy gateway

The live Jev call should be one typed Choice question containing the actual legal action IDs.

The instruction should say, in substance:

- choose only one supplied legal action;
- optimize estimated chance of eventually winning, not immediate damage alone;
- distinguish observed facts from uncertain hypotheses;
- consider immediate and future consequences;
- preserve critical resources when necessary; and
- take calculated risk when the safe line is already losing.

The action criteria should contain facts and consequences, not a strategy verdict.

Optional strategic questions such as “most important threat” or “current risk posture” should initially be used only in offline evaluation or sampled shadow mode. They should not create additional live latency until their value is proven.

Jev’s output remains a candidate ID. It does not create a Showdown command.

### 7. Freshness and legality gate

Before sending the Jev request, store:

- battle ID;
- request ID;
- state version;
- turn number; and
- candidate-set hash.

After Jev responds, compare these values with the current state. If the battle request changed while Jev was thinking, reject the old answer and use the current safe path.

Then validate:

- response schema;
- model/version if required;
- answer type;
- selected ID exists;
- selected ID is legal for the current request; and
- selected order can be serialized by `poke-env`.

### 8. Fast fallback policy

The fallback must be fast, deterministic, and based on verified facts.

Recommended order:

1. Forced legal action.
2. Guaranteed or high-confidence KO.
3. Avoid an immediate known loss.
4. Preserve the only known answer to a major threat.
5. Choose the candidate with the best verified mechanical continuation.
6. Choose the first valid legal order.
7. Use `/choose default` only when no usable decision information exists.

The old `base_power × type_multiplier` rule should not remain the primary fallback. It ignores switching, setup, survival, resources, status, speed, and future consequences.

## Competitive evaluation and improvement loop

The live harness alone cannot establish that the agent is stronger than Foul Play or PokéChamp. Add a separate evaluation loop with the same battle format, team rules, and time budget:

1. **Mechanics and protocol fixtures:** replay known turns and verify state reduction, legal actions, damage ranges, switches, hazards, statuses, and forced-switch handling.
2. **Recorded-state Jev evaluation:** feed Jev saved decision packages so prompt and context changes can be compared without spending an API call on every repeated experiment. Cache identical request/context hashes.
3. **Ablation evaluation:** compare Jev with truth only, truth plus verified mechanics, truth plus beliefs, truth plus response consequences, and the complete context. This detects whether a new feature helps or merely biases the model.
4. **Reference-bot evaluation:** run long series against Foul Play, PokéChamp, and simpler deterministic baselines at controlled strength/settings. Record wins, losses, timeouts, illegal orders, fallback turns, cost, and latency.
5. **Holdout evaluation:** keep unseen teams, seeds, replays, and opponents out of feature tuning. A feature is not an improvement because it wins a few examples it was designed around.

The benchmark must attribute failures to the correct layer:

```text
protocol/state error | mechanics error | belief error | context error
Jev decision error   | timeout/fallback | opponent strength | random outcome
```

Only after Jev-plus-harness performance is measured should we consider adding a live bounded scenario search. If needed, it should generate extra consequence information for Jev or serve as a separately measured policy baseline; it must not silently become a second hand-coded decision-maker.

## Latency design

The harness must be measured, not merely assumed to be fast.

The live path should have these targets:

| Stage | Target |
|---|---:|
| Read current request and canonicalize state | under 100 ms |
| Build legal action registry | under 100 ms |
| Calculate cached/basic mechanical facts | under 300 ms |
| Serialize decision context | under 100 ms |
| Jev network request and inference | bounded, target under 8 seconds |
| Validate and submit order | under 50 ms |
| Fast fallback after timeout | under 100 ms |

These are engineering targets, not claims about current performance. The total decision should target a p95 under 10 seconds and have a hard cutoff far below the available Showdown decision window. The exact budget must be configurable from the remaining request deadline.

Latency rules:

- No serial Jev deliberation in the critical path.
- No live multi-turn search in the first redesign.
- Cache static species, move, type, and format metadata.
- Compute independent deterministic facts in parallel where safe.
- Keep the Jev state compact.
- Do not retry after the deadline is unsafe.
- Make fallback available before starting the external request.
- Record p50, p95, p99, timeout, and fallback latency.

If Jev is slow, the result must be a safe fallback—not a battle timeout.

## Preventing incorrect logic

Every new derived field must pass five checks before it is allowed to influence live Jev decisions:

1. **Definition:** what does the field mean?
2. **Provenance:** which facts produce it?
3. **Units:** percentage, fraction, turn count, probability, category, or unknown?
4. **Oracle test:** can it be checked against Showdown or a trusted mechanics calculation?
5. **Fallback:** what happens when the field cannot be computed?

New features should first run in shadow mode:

- calculate the feature;
- log it;
- do not send it to Jev;
- compare it against replayed battle outcomes; and
- enable it only after its error behavior is understood.

Useful correctness tests include:

- candidate registry versus `battle.valid_orders`;
- request version and stale-response tests;
- exact type and immunity tests;
- known damage-range fixtures;
- hazard and status fixtures;
- forced-switch and waiting-state fixtures;
- unknown-information preservation tests; and
- serialization round-trip tests.

The local scripted WebSocket server should remain a protocol test fixture, but it must not be used as evidence of gameplay correctness. Mechanics tests need a trusted Showdown engine or verified battle fixtures.

## Preventing overfitting and strategic bias

The harness should protect Jev’s intelligence in several ways.

### Do not prune meaningful actions

Only remove illegal actions. Do not remove an action because a local heuristic does not understand it.

### Do not encode the answer in the input

Avoid criteria such as:

```text
Earthquake is the best choice because it is super effective.
```

Prefer:

```text
Earthquake: legal move; 2.0x effectiveness; damage range 70-83%; estimated KO probability 0.72; no status effect; consumes 1 PP.
```

Jev should decide what those consequences mean strategically.

### Keep strategic annotations as hypotheses

If the harness says “likely win condition,” it must include evidence and confidence. It must not be presented as fact or used to remove alternative plans.

### Test feature ablations

Compare Jev with:

- verified state only;
- verified state plus history;
- verified state plus mechanics;
- verified state plus beliefs; and
- the complete context.

If adding a feature causes Jev to choose the same action regardless of position, or causes performance to decline outside the training scenarios, the feature is suspect.

### Detect positional and wording bias

In evaluation, randomize the order of candidate criteria while keeping action IDs stable. If Jev changes choices because an action moved from first to last, the interface is biased.

Use consistent descriptions so one action is not accidentally written more persuasively than another.

### Do not optimize only against one opponent

Evaluate across:

- random seeds;
- different ladder opponents;
- different battle phases;
- different team compositions;
- strong heuristic baselines; and
- held-out battles not used to tune features.

The goal is general decision quality, not a rule that wins a small collection of examples.

## Add, update, and delete decisions

### Add

- Canonical battle-state contract
- Request/version/deadline tracking
- Legal action registry
- Fact provenance and units
- Exact-versus-uncertain outcome representation
- Hidden-information ledger
- Compact relevant-history summary
- Self-describing Jev decision context
- Strict response and stale-response validation
- Fast safety fallback
- Replayable decision package
- Latency and ablation metrics
- Shadow-mode feature rollout process
- Two-plane architecture separating live decisions from offline/shadow search
- Evidence-weighted possible-world compiler with deterministic replayable samples
- Mechanics-oracle contract and differential tests against Showdown
- Reference-bot benchmark harness and failure-layer attribution
- Context/request caching so repeated Jev evaluations do not spend API budget unnecessarily

### Update or refine

- `candidates.py`: reconcile candidates with actual legal orders
- `facts.py`: remove misleading units and expose uncertainty explicitly
- `snapshot.py`: evolve into the canonical decision-context serializer
- `agent.py`: add deadlines, state versions, and freshness checks
- `fallback.py`: use verified safety and continuation facts
- `opencode_jev.py`: use a compact one-call contract with strict validation
- `protocol.py`: version the decision schema
- telemetry: record the exact context and outcome used for every choice
- benchmarks: separate orchestration tests from gameplay and performance evaluation
- simulator/search adapters: keep them behind the oracle boundary and start in offline/shadow mode
- opponent modelling: separate observed, legal-but-unseen, inferred, and sampled-world data
- evaluation: compare Jev-only, Jev-plus-context, and optional search/reference policies on held-out states

### Delete or retire as live decision logic

- Heuristic values labelled as exact damage percentages
- Generic “strongest legal action” wording as the only strategy instruction
- Candidate pruning based on a local heuristic
- `base_power × type_multiplier` as the primary fallback
- Unverified win-condition or opponent-action assertions
- Multiple blocking Jev calls per turn
- Treating the scripted local server as a gameplay simulator
- Treating telemetry parsing as authoritative battle state
- Treating a port of Foul Play MCTS as automatically better than Jev
- Treating PokéChamp-style approximate simulation or Bayesian predictions as authoritative facts
- Making offline search or a reference bot silently override Jev in the live path

Some retired components can remain for diagnostics, but their authority must be removed.

## Implementation sequence

### Phase 0: Baseline and oracle contract

- Freeze the first supported format and ruleset.
- Capture current decision packages, latency, fallback, illegal-order, and outcome baselines.
- Define the canonical state, action, provenance, uncertainty, and mechanics-result schemas.
- Build trusted protocol and mechanics fixtures before adding strategic annotations.
- Decide which local calculations are verified, provisional, or offline-only.

### Phase 1: Truth and safety

- Canonical state fields
- Request metadata
- Action legality parity
- Fact units and provenance
- Stale-response protection
- Strict validation
- Fast fallback
- Latency instrumentation

Do not add ambitious strategy features before this phase is reliable.

### Phase 2: Verified consequence substrate

- Exact legal move and switch registry
- Cached type, move, and format metadata
- Differentially tested damage, KO, speed, hazard, status, and switch-in consequences
- Evidence-weighted hidden-information ledger
- Possible-world compiler with explicit residual unknown mass
- Bounded opponent stay/move/setup/status/switch response summaries

Keep this phase separate from Jev so mechanics bugs can be diagnosed without model judgment.

### Phase 3: Decision context

- Relevant history
- Hidden-information ledger
- Exact and uncertain outcomes
- Neutral semantic glossary
- Compact action consequences

The initial context should remain neutral and avoid hard-coded strategic rankings.

### Phase 4: Jev evaluation

- One-call Choice contract
- Model/schema versioning
- Candidate-order bias tests
- Shadow-mode optional questions
- Ablation tests
- Timeout and fallback measurement

### Phase 5: Offline competitive evaluation

- Replay fixtures
- Trusted mechanics oracle
- Foul Play and PokéChamp reference-bot matches
- Deterministic and heuristic baseline comparisons
- Held-out teams, seeds, and decision states
- Decision-quality and win-rate metrics
- Calibration of Jev probabilities and confidence
- Failure-layer attribution and API-cost accounting

### Phase 6: Optional planning depth

Only if held-out evaluation proves Jev needs more lookahead, add in this order:

- a bounded one-turn scenario compiler;
- a validated local simulator adapter;
- shallow counterfactual lines;
- Jev evaluation at selected search nodes; or
- deeper search as an offline/reference policy.

Every depth upgrade must have a latency budget, ablation result, mechanics-parity evidence, and a clear answer to whether it informs Jev or replaces Jev. These are optional upgrades, not part of the minimum safe live harness.

## Success criteria

The redesigned harness is successful when:

- every submitted order is current and legal;
- no fact is presented with incorrect units or unsupported certainty;
- Jev receives all meaningful legal choices;
- move actions and switch actions are both represented with their actual consequences;
- the opponent’s active choices, revealed bench, fainted Pokémon, and unknown team slots are distinguished;
- opponent moves and switches are represented as uncertain response possibilities rather than hidden assumptions;
- the harness does not encode a preferred answer into the candidate list;
- Jev receives enough semantic information to understand each action’s meaning;
- unknown opponent information remains explicitly uncertain;
- the live decision path stays comfortably inside the battle timer;
- fallback is fast and safer than the current heuristic fallback;
- every decision can be replayed and audited;
- mechanics errors can be separated from Jev judgment errors; and
- performance is measured against real opponents or trustworthy simulators rather than only the scripted local stub.
- offline and live paths produce replayable, schema-versioned decision packages;
- every simulator/search result is classified as Showdown-authoritative, verified-local, or unverified;
- possible-world sampling is reproducible and does not erase high-impact rare threats;
- benchmark results include API cost, fallback rate, latency, and failure-layer attribution; and
- any claimed advantage over Foul Play or PokéChamp survives long held-out series rather than a small set of favorable games.

The success criteria also require that plausible win plans, lose-condition threats, resource criticality, and progress channels are exposed as evidence-backed hypotheses; risk/reward and next-turn continuation are visible without the harness selecting the answer; and information gain and double-switch consequences are represented.

## Simple explanation

The harness should not try to become another Pokémon player sitting beside Jev.

It should become a careful translator and safety system:

1. Showdown tells us what is really happening.
2. The harness translates that into accurate, clearly labelled facts.
3. The harness shows Jev every legal action and what each action can do.
4. Jev makes the strategic choice.
5. The harness checks that the choice is still legal and current.
6. If Jev is slow or unavailable, the harness makes a fast safe choice.

The most dangerous design would be a very complicated harness that confidently gives Jev false calculations, removes actions it does not understand, and takes too long to respond. The best first design is deliberately disciplined: verified facts, explicit uncertainty, full legal choice space, one fast Jev decision, and measurable fallbacks.

## Related research

This design should be read with:

- `docs/research/showdown-harness-current-system-2026-09-20.md`
- `docs/research/jev-ai-typesafe-research-2026-09-20.md`
- `docs/research/pokemon-pro-player-decision-making-and-harness-design-2026-09-20.md`
- `docs/research/foul-play-and-pokechamp-architecture-research-2026-09-21.md`

Those documents explain the current implementation, Jev’s decision-model contract, and expert Pokémon decision-making. This document selects the redesign approach that respects all three project constraints: correctness, preservation of Jev’s intelligence, and battle-time latency.
