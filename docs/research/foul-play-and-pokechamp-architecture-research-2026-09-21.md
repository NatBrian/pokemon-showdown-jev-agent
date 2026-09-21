# Foul Play and PokéChamp Architecture Research

Research date: 2026-09-21

This document records the source-level study of two advanced Pokémon Showdown bots:

- Foul Play: https://github.com/pmariglia/foul-play
- PokéChamp: https://github.com/sethkarten/pokechamp

The purpose is to preserve the research so a future agent can understand both systems without cloning and studying them again. The research is also translated into concrete lessons for the autonomous-pokemon-showdown-jev-agent project, whose decision model is Jev by TypeSafe AI.

## Source snapshots inspected

The repositories were cloned outside the project under `C:\Users\Admin\Documents\Github\_bot-research` so the project code was not modified.

- Foul Play snapshot: commit `6c467c081e862fb321adb405355beb41aba8e226`, dated 2026-09-06.
- PokéChamp snapshot: commit `0f84c460319ebe733f8c3028e58a2a5452c60d85`, dated 2025-10-26.
- Foul Play's `poke-engine` dependency was also inspected: commit `f4e224c`, dated 2026-09-06.

Important local source locations:

- Foul Play: `C:\Users\Admin\Documents\Github\_bot-research\foul-play`
- PokéChamp: `C:\Users\Admin\Documents\Github\_bot-research\pokechamp`
- poke-engine: `C:\Users\Admin\Documents\Github\_bot-research\poke-engine`

The two bots are not the same kind of system. Foul Play is mainly a fast simulator/search bot. PokéChamp is mainly an LLM decision framework with prompts, heuristics, a local simulator, and optional shallow search.

## High-level comparison

| System | Primary strength | Main decision method |
| --- | --- | --- |
| Foul Play | Search over mechanical consequences and hidden opponent worlds | Opponent-set sampling plus Pokémon simulator plus Monte Carlo Tree Search |
| PokéChamp | Presenting rich strategic context to an LLM | Prompt translation plus LLM action selection plus local damage/search helpers |

The most important distinction is this:

```text
Foul Play: truth -> possible worlds -> simulation -> search -> action
PokéChamp: truth -> semantic prompt -> LLM reasoning -> action
```

## Foul Play architecture

Relevant source files:

- `foul-play/fp/main.py`
- `foul-play/fp/run_battle.py`
- `foul-play/fp/websocket_client.py`
- `foul-play/fp/battle/protocol.py`
- `foul-play/fp/battle/state.py`
- `foul-play/fp/search/main.py`
- `foul-play/fp/search/random_battles.py`
- `foul-play/fp/search/standard_battles.py`
- `foul-play/fp/search/poke_engine_helpers.py`
- `foul-play/fp/modes/random_battle.py`
- `foul-play/fp/modes/standard_battle.py`

### Runtime flow

```text
Showdown WebSocket
  -> protocol message parser
  -> custom Battle/Battler/Pokemon state
  -> evidence and opponent-set inference
  -> sampled battle states
  -> poke-engine state conversion
  -> Monte Carlo Tree Search
  -> aggregate action policies
  -> Showdown /choose or /switch command
```

`fp.main.run_foul_play()` configures the bot, applies format-specific modifications, logs into Showdown, loads teams when required, starts a battle, and repeatedly calls `pokemon_battle()`.

`fp.run_battle.pokemon_battle()` receives WebSocket messages. When a request needs a decision, it calls `async_update_battle()`. If the bot must choose, it calls `async_pick_move()` and sends the resulting Showdown command.

### Custom battle state

Foul Play does not send raw Showdown protocol text into the search code. It maintains a detailed custom state containing:

- active and reserve Pokémon
- HP and maximum HP
- status and volatile status
- boosts
- known moves and PP
- last selected and last publicly used moves
- items and abilities
- hazards and other side conditions
- weather and terrain
- Trick Room
- Tera/Mega information
- forced-switch and wait flags
- request ID
- remaining timer
- team-preview state

`fp/battle/protocol.py` dispatches many Showdown events, including switching, moves, damage, healing, fainting, boosts, status, abilities, items, hazards, weather, terrain, Tera, form changes, Z-Moves, volatile statuses, and upkeep.

The parser also performs inference after events. Examples include checking speed ranges, identifying a possible Choice Scarf, identifying Heavy-Duty Boots from hazard behavior, inferring damage ranges, and eliminating impossible sets.

### Hidden-information model

Foul Play distinguishes observed battle facts from possible hidden configurations.

For random battles, `RandomBattleTeamDatasets` loads Randbats data from `pkmn.github.io/randbats`. It stores possible sets for each species, including level, item, ability, four moves, and Tera type.

For standard battles, Foul Play uses datasets derived from Showdown sets, Smogon usage, replay moves, and team configurations.

When the opponent reveals a move, item, ability, speed result, Tera type, or damage result, incompatible configurations can be removed. The remaining configurations are sampled rather than collapsing immediately to one guessed set.

This is the useful pattern:

```text
Observed evidence
  -> remove impossible hypotheses
  -> retain multiple plausible hypotheses
  -> search across weighted possible worlds
```

### Foul Play search

`fp/search/main.py` performs the main search:

1. Deep-copy the current battle.
2. Ask the active format mode how many scenarios and how much search time to use.
3. Prepare multiple possible battles by filling in hidden opponent sets.
4. Convert each battle to a `poke-engine` state.
5. Run Monte Carlo Tree Search in worker processes.
6. Collect root action visit policies.
7. Weight each policy by the probability of its sampled world.
8. Keep actions that are sufficiently close to the best aggregate policy.
9. Randomly select from the retained policy using its weight.

The number of sampled scenarios changes with information and time pressure. In random battles, early turns with few revealed opponent moves use more shallow scenarios. When the timer is low, the search budget is reduced.

Foul Play's action selection is therefore not simply “choose the highest base-power move.” It considers moves and switches through simulated future states.

### poke-engine

Foul Play converts its Python battle state into the Rust-based `poke-engine` state. The engine represents both sides, Pokémon, moves, statuses, boosts, hazards, weather, terrain, Trick Room, switching, and battle resources.

The engine supports:

- legal move and switch generation
- damage calculation
- damage-roll branching
- instruction generation for uncertain mechanics
- MCTS
- iterative-deepening expectiminimax
- heuristic state evaluation

The MCTS implementation uses UCB-style action selection, branches on possible damage or mechanic outcomes, performs rollouts using an evaluation function, and backpropagates scores to root actions.

Its evaluation function assigns values to factors such as:

- remaining HP
- remaining Pokémon
- status conditions
- attack, defense, special attack, special defense, and speed boosts
- Substitute
- Leech Seed
- hazards
- screens
- Tailwind
- Healing Wish
- Tera usage

### Foul Play strengths

- Detailed event-based state tracking.
- Strong separation between known facts and hidden hypotheses.
- Fast compiled battle simulation.
- Search over switches as well as moves.
- Explicit handling of damage and mechanic uncertainty.
- Format-specific data and search budgets.
- No need for an LLM to know Pokémon rules.

### Foul Play limitations for our project

- Its search engine already makes the final strategic choice, which can duplicate Jev.
- Its scoring weights are hand-coded and can encode its own biases.
- Its inferred sets depend on external datasets and their freshness.
- Its simulator must be tested against the exact Showdown format before being treated as authoritative.
- Its random selection among near-best actions introduces variance.
- Porting the entire system would be substantially more complex than extending the current Jev harness.

## PokéChamp architecture

Relevant source files:

- `pokechamp/scripts/battles/showdown_ladder.py`
- `pokechamp/scripts/battles/local_1v1.py`
- `pokechamp/pokechamp/llm_player.py`
- `pokechamp/pokechamp/prompts.py`
- `pokechamp/poke_env/player/local_simulation.py`
- `pokechamp/pokechamp/minimax_optimizer.py`
- `pokechamp/pokechamp/timeout_llm_player.py`
- `pokechamp/bayesian/team_predictor.py`
- `pokechamp/poke_env/player/team_util.py`

### Runtime flow

```text
Showdown/poke-env battle state
  -> LocalSim copy
  -> state and action prompt generation
  -> LLM or heuristic decision
  -> JSON parsing and action matching
  -> optional shallow tree search
  -> BattleOrder
  -> Showdown
```

The ladder script creates a player through `get_llm_player()`. For online PokéChamp battles, the factory normally uses `TimeoutLLMPlayer`, which wraps `LLMPlayer` and falls back to a fast heuristic if the LLM takes too long.

### Prompt contents

PokéChamp can provide the LLM with:

- recent battle history
- active Pokémon and opponent
- types
- HP
- status
- abilities
- items
- boosts
- calculated stats
- speed comparison
- known opponent moves
- possible opponent moves
- legal moves
- legal switches
- switch Pokémon HP and stats
- switch Pokémon types and moves
- type effectiveness
- hazards
- weather and terrain
- strategic instructions

The prompt also contains competitive concepts such as:

- setting up only when safe
- using hazards
- removing hazards
- attacking a boosted opponent quickly
- accounting for switch-in damage
- recognizing that switching gives the opponent an action
- recognizing that a slower switch-in can allow the opponent to move repeatedly

These concepts are useful as semantic labels for Jev, but they should not be converted into unconditional rules.

### Action validation

The LLM returns JSON such as:

```json
{"move":"earthquake"}
```

or:

```json
{"switch":"rotomwash"}
```

The response is matched against available moves or available switches. If parsing or matching fails repeatedly, PokéChamp falls back to a heuristic action.

This establishes an important pattern for Jev: the decision model may name an action, but the harness must map it to an exact legal action and reject invalid output.

### LocalSim

PokéChamp includes a local simulator and damage calculator. `LocalSim` deep-copies the battle, estimates damage, calculates turns to faint, compares speed, and applies simplified state changes.

The simulator is not the official Showdown simulator. Its `step()` function manually creates simplified battle-message-like updates for switches, moves, damage, and some statuses. It is intended to support fast reasoning and shallow search, not to replace Showdown as the authoritative referee.

This is the main technical risk of copying PokéChamp directly: a fast but approximate simulator can supply confidently wrong consequences.

### Opponent prediction

PokéChamp includes a Bayesian team predictor trained from large team datasets. It estimates:

- likely unrevealed teammates
- likely moves
- likely items
- likely abilities
- likely nature
- likely EV spread

The predictor counts species, teammate relationships, and per-species configurations. It can use observed moves to adjust configuration probabilities.

In the battle prompt, confirmed and predicted moves can be combined. For Jev, this must be improved into explicitly labelled categories:

```text
observed: earthquake, source=Showdown, confidence=1.0
predicted: stealthrock, source=dataset, confidence=0.42
legal-but-unseen: recover, source=species movepool, confidence=unknown
```

### PokéChamp minimax mode

PokéChamp can perform a shallow LLM-guided tree search:

1. Copy the battle into a local simulator.
2. Generate a small set of player actions.
3. Estimate a small set of opponent actions.
4. Simulate combinations.
5. Ask an LLM or heuristic to score future states.
6. Select the best-scoring action.

The optimized implementation limits the number of actions for performance. It commonly considers a damage-calculator action and one LLM-selected action, plus a small number of predicted opponent actions.

Therefore this is not an exhaustive minimax search over every legal Pokémon action. It is a shallow, LLM-guided scenario search.

The repository also contains an optimizer with state hashing, object pooling, and cache structures. However, the current tree-search code does not consistently use all of the cache methods. These structures should be treated as optimization scaffolding, not proof that the search is fully cached.

### Timeout and fallback

`TimeoutLLMPlayer` runs the LLM path and fallback path concurrently. If the LLM exceeds the configured timeout, the fallback action is returned.

This is a good operational idea. However:

- the default online timeout is approximately 90 seconds;
- the normal decision may perform retries or multiple LLM calls;
- cancelling a running thread does not necessarily stop the underlying model request;
- several slow calls can continue in the background.

This is not appropriate for our Jev live path without a much smaller hard deadline and request cancellation strategy.

### PokéChamp strengths

- Rich semantic prompt construction.
- Explicit action and switch choices.
- Good presentation of matchup, speed, hazards, and status concepts.
- Bayesian hidden-information guesses.
- Multiple decision modes for experimentation.
- Precomputed fallback concept.
- Local battle evaluation and offline bot-vs-bot testing.

### PokéChamp limitations for our project

- Approximate local mechanics can be wrong.
- Predicted information is not always clearly separated from observed information.
- Prompt text can bias the model toward fixed strategies.
- Minimax branches are intentionally pruned.
- Multiple LLM calls create latency and cost.
- Base-power fallback is strategically weak.
- State hashes omit much of the complete battle state.
- Some optimizer and logging paths are incomplete or fragile.

## Lessons for the Jev harness

Our Jev harness should combine the strongest architectural ideas without copying either bot wholesale.

### Recommended architecture

```text
Showdown/poke-env authoritative state
  -> canonical battle reducer
  -> exact legal action registry
  -> validated mechanics/consequence calculator
  -> observed-fact ledger
  -> hidden-information belief ledger
  -> compact strategic consequence summary
  -> one Jev Choice request
  -> strict action validation
  -> immediate deterministic fallback
```

### What to borrow from Foul Play

- Detailed battle-event state reducer.
- Separate facts from hypotheses.
- Track opponent Pokémon, moves, items, abilities, and possible sets.
- Remove impossible hypotheses when evidence appears.
- Use scenario sampling or bounded scenario summaries.
- Calculate consequences before asking the decision model.
- Keep legal action generation separate from strategy.
- Use deterministic and measured time budgets.

### What to borrow from PokéChamp

- Explain Pokémon concepts in plain language.
- Provide move and switch actions separately but in the same decision set.
- Include speed order and switch-in consequences.
- Include short battle history.
- Include hazards, status, boosts, and resource information.
- Label strategic concepts such as KO threat, setup threat, progress, and preservation.
- Validate the model response against the exact legal action registry.
- Prepare a fallback before the remote decision request finishes.

### What Jev should receive

Jev should receive a compact structured decision state containing:

- every meaningful legal move action;
- every legal switch action;
- active Pokémon and exact status;
- own team and resource state;
- revealed opponent Pokémon;
- unknown opponent slots;
- observed opponent moves and effects;
- possible opponent actions with confidence and source;
- damage and KO ranges with units;
- speed-order ranges;
- switch-in damage and hazard consequences;
- best, likely, and catastrophic opponent responses;
- win-condition and lose-condition hypotheses;
- Tera/resource implications;
- explicit unknown fields.

Jev should decide the strategy. The harness should not decide that one move is always best.

### Three project constraints

#### Wrong information

Every inferred value must carry:

- source;
- unit or representation;
- confidence or probability;
- observed/calculated/inferred/unknown status.

Predicted moves must never be presented as confirmed moves. An approximate simulator result must never be presented as exact unless it has been validated against Showdown.

#### Overfitting

The harness should:

- expose all meaningful legal moves and switches;
- expose consequences instead of final verdicts;
- avoid a large hand-coded Pokémon playbook;
- keep strategic annotations as hypotheses;
- test action-order bias;
- compare Jev decisions with and without optional annotations;
- avoid pruning merely because one action looks best to the harness.

#### Latency

The live path should use:

- one compact Jev request per turn;
- cached static Pokémon and move data;
- bounded local computation;
- no live Monte Carlo tree search unless explicitly budgeted;
- a hard Jev deadline;
- stale-response rejection;
- an immediate deterministic fallback.

Foul Play-style scenario generation and deeper search are better suited to offline analysis, replay study, shadow evaluation, or optional bounded precomputation than to an unbounded live request path.

## Final conclusion

Foul Play shows how to build a reliable Pokémon reasoning substrate:

```text
authoritative state + hidden-world inference + mechanical search
```

PokéChamp shows how to translate that substrate into language understandable by a decision model:

```text
semantic state + strategic context + explicit actions
```

For the Jev project, the best design is:

```text
Foul Play’s state, evidence, and consequence discipline
+ PokéChamp’s semantic explanations and strategic context
- approximate mechanics as truth
- unlabelled predictions
- repeated live LLM calls
- hard-coded final action verdicts
```

The goal is not to make Jev imitate either bot. The goal is to give Jev a trustworthy, compact, low-latency representation of the same information that makes those systems strong, while preserving Jev’s ability to choose the strategy.
