# Phase 1 Research and Architecture

Date checked: 2026-09-19  
Status: Research and proposed design; implementation has not started.

This document is the project memory for the Phase 1 investigation. It is intended to prevent a future contributor or agent from repeating the same research. It records what was verified, what is recommended, what remains an assumption, and the boundaries for the first implementation.

## 1. Executive decision

The recommended implementation is:

~~~
Python 3.10+
    |
    +-- poke-env Player -------------------- Showdown WebSocket/server
    |       |
    |       +-- battle state and legal orders
    |       +-- async choose_move hook
    |
    +-- deterministic candidate/evaluation layer
    |       |
    |       +-- legal-action enumeration
    |       +-- type, damage, speed, priority, hazard, and tera facts
    |       +-- fallback order selection
    |
    +-- Jev adapter ------------------------ OpenCode Zen /systemone
            |
            +-- typed Choice/Score/Noul questions
            +-- confidence and probability telemetry
~~~

Use poke-env for the first live harness. Call Jev directly through the OpenCode Zen System One endpoint with an asynchronous HTTP client. Do not route decisions through opencode run or a normal chat/agent loop.

The first agent should ask Jev to choose among a small set of already-legal, already-annotated candidate actions. Jev should not be responsible for parsing raw Showdown protocol, looking up type-chart arithmetic, calculating exact damage, or inventing an order string.

## 2. Verified Jev/OpenCode findings

### 2.1 Working route

The following route was probed successfully from the local environment:

~~~
POST https://opencode.ai/zen/v1/systemone
Authorization: Bearer public
Content-Type: application/json
~~~

The model identifier used by the free route is:

~~~
jev-1.13-free
~~~

The probe did not require a TypeSafe API key. The response reported cost "0" and returned typed answers, confidence, probabilities, and token usage.

This proves that the route was available at the time of the probe. It does not prove unlimited quota, permanent availability, or a service-level latency guarantee. The client must treat quota, model availability, HTTP errors, and endpoint-contract changes as normal failure modes.

### 2.2 Request shape

Jev is a typed decision API, not a normal text-generation API. The important top-level fields are model, structured state, and typed questions.

Minimal example:

~~~json
{
  "model": "jev-1.13-free",
  "state": {
    "active_pokemon": "Garchomp",
    "opponent_pokemon": "Heatran"
  },
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Choose the strongest legal action.",
      "criteria": {
        "move_earthquake": "Use Earthquake.",
        "switch_rotom": "Switch to Rotom-Wash."
      }
    }
  }
}
~~~

For this project, criteria should contain only stable candidate IDs and short descriptions. The candidate IDs are the interface between Jev and the battle adapter; they must never be raw, model-generated protocol strings.

The API documentation describes typed choice, score, and noul/Boolean questions. It also supports multiple questions in one request. The project should initially use one choice question and add other question types only when their telemetry has a clear evaluation purpose.

### 2.3 Response handling

Expected response data includes:

~~~json
{
  "answers": {
    "action": {
      "type": "choice",
      "choice": "move_earthquake",
      "confidence": 0.91,
      "probabilities": {
        "move_earthquake": 0.91,
        "switch_rotom": 0.09
      }
    }
  },
  "usage": {
    "input_tokens": 309,
    "output_tokens": 24
  },
  "cost": "0"
}
~~~

The adapter must validate all of the following before accepting the answer:

1. The response is valid JSON and has the expected typed answer.
2. The selected ID exists in the request's candidate map.
3. The candidate is still legal for the current battle request.
4. Confidence and probabilities are numeric and within sensible bounds.
5. The answer corresponds to the current request correlation ID/state version.

If any check fails, select a legal deterministic fallback and record the reason.

### 2.4 The normal OpenCode CLI path is not the Jev transport

The command below was tested:

~~~
opencode run --model opencode/jev-1.13-free
~~~

It produced a provider-side HTTP 500/OpenCode provider.internal error. The likely design mismatch is that the normal path expects a conversational model protocol, while Jev expects System One typed-decision input. Therefore:

- OpenCode is still the service/provider route we use.
- The Jev System One endpoint is the transport for battle decisions.
- opencode run is not part of the battle-turn critical path.

The direct HTTP implementation should be isolated behind a JevProvider interface so a future endpoint or paid provider can be substituted without changing the battle agent.

### 2.5 Recommended Jev client behavior

The eventual client should:

- use a reusable httpx.AsyncClient or aiohttp session;
- use an explicit short timeout suitable for the Showdown move timer;
- avoid blocking subprocess calls inside the asyncio loop;
- include a request ID, battle ID, turn number, and state schema version in local telemetry;
- never log authorization headers or secrets;
- record model ID, HTTP status, latency, reported token usage, reported cost, and fallback reason;
- retry only safe transient failures, and avoid retry storms near a move deadline;
- return a typed internal result rather than exposing raw provider JSON to the battle layer.

## 3. Pokémon Showdown and Gen 9 Random Battles

### 3.1 Showdown protocol facts

Showdown communicates through room messages over a WebSocket/SockJS-compatible protocol. Messages are room-prefixed and use pipe-delimited commands. The protocol includes authentication/challenge handling, room joining, search requests, battle requests, choices, errors, and updated requests.

Important battle concepts for the adapter:

- A battle turn is represented by a request from the server.
- A client submits an order with /choose ... or the equivalent room command.
- A request can include active move options, switch options, disabled moves, PP, side Pokémon, conditions, and the request ID (rqid) where supplied.
- The server can respond with an error followed by a new request when an order is invalid or stale.
- Team preview and ordinary move requests are distinct request states; the adapter must not assume every request is a normal single move choice.

The first implementation should not parse raw WebSocket frames itself. poke-env already implements the protocol-facing client and exposes a battle-oriented object model. Raw protocol knowledge remains important for diagnosing logs and handling edge cases.

### 3.2 Why poke-env is the first harness

poke-env is a Python library for scripted Pokémon agents and supports:

- Showdown connection and authentication;
- battle objects and battle lifecycle management;
- legal available moves and switches;
- asynchronous choose_move implementations;
- player subclasses and battle formats;
- random and heuristic player examples;
- battle order objects, including move, switch, and Terastallization variants;
- a Gen 9 damage-calculation module.

The relevant format string is:

~~~
gen9randombattle
~~~

For development and benchmarking, use a private/local Showdown server. Public servers are useful for a later smoke test, but are unsuitable as the first deterministic benchmark environment because of rate limits, matchmaking variability, network failures, and changing opponents.

### 3.3 Random Battle information constraints

Random Battles are imperfect-information games. The agent must distinguish:

- facts directly revealed by the battle protocol;
- facts inferred from observed moves, damage, abilities, items, or team composition;
- facts that are still unknown.

The state serializer must never turn an inference into a false fact. Every uncertain field should either be omitted or represented with an explicit uncertainty marker/distribution. In particular, do not include the opponent's unrevealed species, moves, item, ability, EVs, or tera type as if known.

The Showdown random-battle data is useful for understanding generated team sets, but the live agent should use only information legally available from the current battle plus clearly marked prior knowledge allowed by the project rules.

## 4. Division of labor: deterministic engine versus Jev

### 4.1 Responsibilities kept outside Jev

The harness and deterministic evaluator should own:

- extracting the current request from poke-env;
- enumerating legal moves and legal switches;
- checking whether Terastallization is currently available;
- identifying disabled moves and zero-PP moves;
- type effectiveness and immunity checks;
- damage range calculations where the required data is known;
- speed/priority relationships when determinable;
- hazard, weather, terrain, screens, status, and stat-stage features;
- candidate IDs and their exact BattleOrder objects;
- stale-request detection;
- final legality validation;
- safe fallback behavior.

This is not just an optimization. It prevents Jev from hallucinating an illegal order or wasting decision capacity on arithmetic that the program can calculate exactly.

### 4.2 Responsibilities given to Jev

Jev should evaluate strategic tradeoffs such as:

- whether to attack, switch, or use setup/utility;
- whether preserving a Pokémon is more valuable than maximizing immediate damage;
- whether to take a risk based on the current win condition;
- whether to reveal or preserve Terastallization;
- whether a likely opponent switch changes the best action;
- whether this is a favorable position, neutral position, or desperation turn.

Jev is selecting from a constrained action set, not writing a battle plan in free-form text.

### 4.3 Candidate action abstraction

Each legal action should have a stable internal record similar to:

~~~json
{
  "id": "move_earthquake",
  "kind": "move",
  "order_ref": "internal-order-object",
  "label": "Use Earthquake",
  "facts": {
    "power": 100,
    "accuracy": 100,
    "stab": true,
    "super_effective": true,
    "estimated_damage_percent": [72, 85],
    "estimated_ko": false,
    "priority": 0
  }
}
~~~

The order_ref is an in-memory object and must never be sent to Jev. Jev receives the ID and compact facts. After Jev returns the ID, the adapter retrieves the order object from the current candidate map.

Stable IDs are preferable to natural-language labels because they make validation, logging, replay, and benchmark analysis reliable. Candidate IDs must be unique within a request and can be discarded after the request ends.

## 5. State serialization design

### 5.1 State schema goals

The serialized state should be:

- compact enough for low latency;
- explicit about unknown information;
- deterministic and versioned;
- easy to inspect in logs and replay fixtures;
- independent of Jev-specific wording as much as practical;
- derived from the current information set, not hidden simulator state.

Every request should include a schema version, for example:

~~~json
{
  "state_schema": 1,
  "battle_format": "gen9randombattle",
  "turn": 8,
  "request_id": "battle-abc:8:rqid-12"
}
~~~

### 5.2 Recommended state sections

The first version should include:

~~~
match
  format, turn, request type, weather, terrain, field effects

self
  active Pokemon, HP fraction, status, stat stages
  revealed team members, alive/fainted state
  known item/ability/moves, tera availability and known tera type

opponent
  active Pokemon and observed condition
  revealed team members, alive/fainted state
  only observed or explicitly inferred information
  unknown fields marked unknown

battle_facts
  hazards, screens, speed/priority facts
  deterministic damage/KO estimates
  relevant immunities, resistances, and weaknesses

legal_actions
  candidate ID, kind, short label, deterministic annotations

history_summary
  compact recent actions, revealed moves, notable damage/status events
~~~

Do not send the entire raw protocol transcript on every turn. Store raw messages separately for debugging and replay. Send only the current state and a compact history summary that affects the decision.

### 5.3 Context and criteria usage

Use the Jev state for facts and the choice.criteria map for candidate-specific definitions. For example:

~~~json
{
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Choose the action that best preserves a winning line while considering the supplied deterministic facts.",
      "criteria": {
        "move_earthquake": "Attack with Earthquake; estimated damage 72-85%; no immediate KO.",
        "move_stealth_rock": "Set Stealth Rock; opponent has 3 revealed switch-sensitive targets.",
        "switch_rotom": "Switch to Rotom-Wash; estimated incoming damage is low, but lose current tempo."
      }
    }
  }
}
~~~

Keep criteria descriptions short and factual. The state should contain shared facts; criteria should distinguish actions. Avoid repeating the complete battle state in every criterion.

The initial version should send one choice question. A later experiment may add:

- a score question for position quality;
- a Boolean/noul question for whether the turn is a desperation turn;
- an independent risk question for calibration studies.

Additional questions should be added only if they improve measured decisions or calibration enough to justify extra payload and latency.

## 6. Asynchronous execution and timer safety

poke-env allows choose_move to return an awaitable, which makes it suitable for a non-blocking Jev call. The battle decision path should be:

~~~
Showdown request
  -> poke-env exposes Battle
  -> snapshot serializer
  -> legal candidate builder
  -> deterministic annotations
  -> async Jev HTTP request
  -> response validation
  -> BattleOrder lookup
  -> poke-env sends legal order
~~~

Required safeguards:

1. Reuse one async HTTP client rather than creating a new connection per turn.
2. Set a deadline shorter than the server's remaining move time.
3. Reserve time for validation and order submission.
4. Cancel or ignore an in-flight decision when a newer request supersedes it.
5. Include battle ID, turn, and request/rqid in the correlation key.
6. Never call a blocking CLI process from choose_move.
7. Use a deterministic legal fallback on timeout, HTTP failure, invalid JSON, invalid choice, or stale state.
8. Keep one battle's decision requests serialized; add concurrency only after correctness is established.

The fallback should be predictable and legal. A reasonable first fallback priority is:

~~~
legal forced action
  -> safe legal move with strongest deterministic immediate outcome
  -> legal switch selected by deterministic heuristic
  -> first legal action as a final safety net
~~~

The exact fallback policy is a benchmark variable and must be logged.

## 7. Error and edge-case inventory

The implementation must explicitly handle:

- team preview or non-move requests;
- forced switches after a faint;
- disabled moves and zero PP;
- no legal switch options;
- moves that require a target or special order syntax;
- Terastallization availability and the one-use-per-battle constraint;
- status, confusion, trapping, recharge, and other forced-action conditions;
- server-side rejection of a stale or invalid choice;
- reconnects and battle-room termination;
- provider timeout, rate limit, 4xx, 5xx, malformed response, and quota exhaustion;
- a model returning a candidate ID with the wrong type or casing;
- hidden opponent information accidentally appearing in debug/state output;
- request state changing between serialization and order submission;
- a battle ending while a Jev request is in flight.

The order validator is the final authority. No Jev output should be converted directly into a raw /choose string.

## 8. Proposed repository structure

The current repository is documentation-only. After architecture approval, the implementation can use:

~~~
pyproject.toml
src/
  jev_showdown/
    __init__.py
    agent.py
    battle/
      __init__.py
      snapshot.py
      candidates.py
      serializer.py
      validator.py
    decision/
      __init__.py
      protocol.py
      opencode_jev.py
      fallback.py
    strategy/
      __init__.py
      heuristics.py
    telemetry/
      __init__.py
      events.py
tests/
  fixtures/
  unit/
  integration/
benchmarks/
  run_matches.py
  analyze.py
docs/
  research/
  architecture/
  benchmarking.md
~~~

Recommended separation:

- battle/ knows Pokémon battle facts and legal orders.
- decision/ knows Jev/OpenCode request and response contracts.
- strategy/ contains deterministic baselines and fallback policy.
- telemetry/ defines structured events without leaking secrets.
- benchmarks/ runs match batches and computes metrics.

## 9. Benchmark design

### 9.1 Baselines and ablations

The first benchmark matrix should include:

1. Random legal-action baseline.
2. Deterministic damage/utility heuristic baseline.
3. Jev with compact state and deterministic candidate annotations.
4. Jev ablation without damage annotations.
5. Jev with fallback behavior measured separately from normal decisions.

poke-env provides random and heuristic player patterns that can help bootstrap these baselines, but the benchmark runner should own the final Gen 9 Random Battles configuration rather than assuming an example's generation or format.

### 9.2 Match environment

Use a local Showdown server for the main benchmark. Pin the Showdown revision, format, bot versions, and match settings. Record the random seed or replay identifier where the server supports deterministic replay. Run public-server games only as a separate connectivity smoke test.

Avoid using ladder win rate as the primary scientific result. Ladder opponents and server conditions are not controlled, and they make it difficult to attribute changes to the Jev policy.

### 9.3 Metrics

Record at least:

~~~
win rate and confidence interval
average turns per battle
median and p95 decision latency
provider timeout/error rate
fallback rate and fallback reason
illegal/stale order rate
reconnect or dropped-battle rate
reported input/output tokens
reported provider cost
calibration error for confidence/probability outputs
~~~

For calibration, define the prediction target before collecting results. Options include:

- whether the selected action eventually wins the battle;
- whether the selected action produces an immediate tactical success;
- one-step outcome labels from a deterministic simulator or controlled replay.

Whole-battle win/loss is a noisy target for individual-turn confidence, so the report should distinguish action-level calibration from final match performance. Use reliability diagrams, Brier score, and log loss where probabilities are available.

### 9.4 Statistical discipline

Start with a small smoke batch to catch protocol and implementation errors. Then run a predeclared larger batch per matchup, with the same environment and seeds for competing agents where possible. Report sample sizes and uncertainty; do not claim superiority from a handful of games.

The exact sample size should be selected after the baseline win rate and variance are known. A practical first serious run is hundreds of matches per matchup, followed by a power calculation for a larger comparison if the difference is small.

## 10. Alternatives considered

### Direct raw Showdown WebSocket client

Advantages:

- maximum protocol control;
- potentially simpler deterministic replay integration;
- no dependency on poke-env abstractions.

Disadvantages:

- authentication, rooms, requests, orders, reconnects, and battle parsing become project code;
- much larger protocol surface and more opportunities for illegal orders;
- slower path to a reliable first battle.

Decision: do not use for the MVP. Reconsider only if poke-env prevents a required Gen 9 behavior or if a specialized replay engine is needed.

### Showdown simulator CLI without a live server

Advantages:

- fast deterministic tests;
- useful for fixtures and offline decision evaluation;
- avoids WebSocket timing during unit tests.

Disadvantages:

- does not validate login, room lifecycle, request handling, or real timers;
- may not provide the same information boundary as the live player API.

Decision: use as a secondary test/fixture mechanism, not as the only harness.

### Normal OpenCode agent/chat loop

Decision: rejected for Jev battle decisions because the verified CLI path failed with a provider internal error and does not match Jev's typed System One contract.

## 11. Open questions and assumptions

These items should be resolved during implementation or explicitly pinned in configuration:

- exact timeout budget for the selected local/public server;
- whether the free Jev route imposes undocumented request or concurrency limits;
- exact response fields and error formats for all Jev failure cases;
- which damage calculator inputs are available from revealed random-battle information;
- whether the benchmark server exposes a stable seed/replay control suitable for paired tests;
- whether the policy is allowed to use prior random-battle set knowledge, and how that affects information-set labeling;
- the final fallback heuristic and whether fallback turns are included in Jev performance metrics.

These are not reasons to block the architecture. They should be represented as configuration and tested explicitly rather than hidden assumptions.

## 12. Phase 1 conclusion and implementation gate

The architecture is ready for review. The project should proceed only after confirming:

- direct OpenCode System One is the Jev transport;
- poke-env is the initial Showdown harness;
- Jev chooses among validated candidate IDs;
- deterministic battle math remains outside Jev;
- local Showdown is the primary correctness and future controlled-evaluation environment, while public Showdown is used for real-opponent showcase evidence;
- every provider or model failure has a legal fallback.

After approval, the next document should be an implementation plan with milestones and tests. Only after that plan is approved should source code be added.

## 13. Clarification: opponent and benchmark scope

The project does not need to build a second bot in order to demonstrate Jev. The Jev agent can play Gen 9 Random Battles through Showdown's normal matchmaking or through a human challenge. Showdown's protocol supports `/search gen9randombattle`, and Random Battle does not require a user-supplied team. The public ladder records Elo, GXE, and Glicko-1, while Showdown also exposes JSON endpoints for user ratings, ladders, and replays.

The benchmark plan is therefore split into three levels:

1. **MVP correctness:** prove that Jev can connect, receive the real information set, choose legal actions, and complete battles without timing out. This can use a local Showdown server for protocol smoke tests and the public server for a real-opponent smoke test.
2. **Showcase evidence:** record a live Gen 9 Random Battle against a public matchmaking opponent or human challenger. The local browser dashboard makes the Jev input, typed output, action, and result visible.
3. **Future controlled evaluation:** run Jev against existing open-source agents or `poke-env` reference players, copied or configured as external test opponents. We do not build those comparison agents in the current project phase.

Public ladder ratings are useful external evidence, but they are not a controlled scientific comparison. Showdown itself explains that Elo/GXE depend on the opponent pool and that raw win/loss is not a good skill estimate. Therefore, the project should report a Jev account's format, rating system, number of games, date, and replay links rather than presenting one short ladder run as proof of universal superiority.

For automated batches, a private/local server remains safer and more reproducible. Public-ladder automation must respect the current Showdown rules and server policy; do not intentionally manipulate ratings, farm games, or run uncontrolled high-volume traffic. The official rules prohibit cheating and gaming the system, and this project should treat public play as a limited smoke/showcase path until bot use is explicitly confirmed as acceptable.

This clarification replaces the earlier assumption that a simple local scripted opponent must be part of the MVP.

## 14. Current opponent and evaluation decision

The project will use two distinct modes:

### Public showcase mode

The dashboard's main **Start Jev Battle** flow searches the public Showdown Gen 9 Random Battle ladder. This demonstrates Jev in the real game environment against a matchmaking opponent. The battle result can be accompanied by a replay link and, over a larger run, the Jev account's Elo/GXE/Glicko-1 information.

### Controlled development mode

For repeatable correctness and strength checks, Jev will play against the existing `poke-env` reference players on a local Showdown server. We are not writing these bots:

- `RandomPlayer` is a connectivity and legality smoke-test opponent.
- `SimpleHeuristicsPlayer` is the first meaningful provided baseline for Jev.
- `MaxBasePowerPlayer` can be considered later as an additional simple reference.

The `poke-env` package exports these players and provides battle/cross-evaluation utilities. This gives us a controlled opponent without adding a second strategic system to this repository.

### What each mode proves

| Mode | Opponent | What it proves |
| --- | --- | --- |
| Local smoke test | `RandomPlayer` | Connection, state tracking, legal orders, battle completion |
| Local benchmark | `SimpleHeuristicsPlayer` | Jev's decisions against a known reproducible heuristic baseline |
| Public showcase | Matchmaking opponent | Jev operates in the real public Gen 9 Random Battle environment |
| Human challenge | Human player | Qualitative real-world demonstration, not a controlled benchmark |

A single human match cannot establish that Jev is as strong as a human. Human comparability requires a sustained public-ladder run or a future controlled match set against established agents, with game count, rating uncertainty, dates, and replay evidence reported.

## 16. Refined harness, deterministic evaluator, and Jev contract

The word harness refers to more than the `poke-env` dependency. The project boundary is:

~~~
Showdown server
    -> poke-env battle adapter
    -> deterministic evaluator
    -> Jev decision adapter
    -> legal-order validator
    -> Showdown order
~~~

`poke-env` supplies the battle-facing state and order interface. Its battle object exposes the active Pokémon, available moves, available switches, field/weather state, side conditions, team state, current request, turn, Terastallization availability, and battle result. Its Pokémon and Move objects expose known types, HP, status, stat boosts, known moves, items/abilities when revealed, move type, category, power, accuracy, priority, PP, and related move effects.

The deterministic evaluator is a thin project layer around that state. It computes legal candidate records and derived facts such as type effectiveness, immunity, STAB, damage ranges, estimated KO status, priority, speed facts when known, hazard/status consequences, switch safety, and Tera legality. It does not make the strategic decision.

The Gen 9 calculator in `poke-env` can return minimum and maximum possible damage rolls. Its documentation also notes that some edge cases are ignored and behavior may deviate from the official calculator. Therefore, the project must display damage as a calculated range or estimate with assumptions, not as universally exact truth. Unknown opponent items, abilities, EVs, IVs, or exact stats must remain unknown or conditional.

Jev receives a compact information-set snapshot, not raw protocol text. The snapshot contains the current turn/request, public self and opponent state, field conditions, legal candidate action IDs, deterministic annotations, uncertainty markers, and a typed Choice question. Jev does not receive hidden server state, raw in-memory order objects, or permission to invent illegal actions.

For the MVP, Jev returns one typed action choice with confidence and probabilities. The application then validates the candidate ID, maps it to the current legal order, and sends it to Showdown. Provider errors, malformed answers, stale requests, and timeouts use a legal fallback.

## 17. Observable pipeline and dashboard truth

The dashboard should expose this complete application pipeline:

~~~
OBSERVE
  Showdown state and public information
      ->
CALCULATE
  deterministic facts and action annotations
      ->
PRESENT OPTIONS
  legal moves, switches, and Tera variants
      ->
JEV DECIDES
  typed choice, confidence, probability distribution
      ->
VALIDATE
  candidate and current-request legality checks
      ->
ACT
  exact BattleOrder submitted to Showdown
      ->
RESULT
  damage, status, switch, faint, or win/loss update
~~~

This is the truthful observable pipeline. We can show the complete Jev input, question criteria, deterministic facts, Jev output, validation result, action, timing, usage, cost, and result. We cannot show internal latent computation or hidden chain-of-thought that Jev does not return, and the dashboard must not fabricate it.

## 18. Dashboard design consequence

The interface should make the observable pipeline understandable without
turning it into a generic analytics product. The exact composition is
intentionally open. Preserve the following behavior regardless of visual
solution:

- distinguish `Showdown state`, `Calculated by harness`, `Jev output`, and
  `Adapter action`;
- expose the typed choice, returned metadata, validation, submitted order, and
  observed result;
- provide structured inspection for technical viewers; and
- never imply access to hidden reasoning that Jev does not return.

See [the dashboard product contract](../design/dashboard-product-contract.md)
for the current authority.

## 15. Reproducible difficulty progression

Pokémon Showdown has a public rated ladder, but it does not provide a fixed sequence of opponents labeled easy, medium, and hard. Public matchmaking selects opponents from the active player pool, and the difficulty changes with the population, rating, time, and account history. Elo, GXE, and Glicko-1 summarize performance; they are not a scripted difficulty ladder.

The project can provide the desired progression locally without building new opponent logic. The evaluation harness can run the Jev agent against existing `poke-env` players in a fixed order:

1. **Easy / smoke:** `RandomPlayer`.
2. **Tactical:** `MaxBasePowerPlayer`.
3. **Heuristic:** `SimpleHeuristicsPlayer`.
4. **Future advanced:** an existing external Gen 9 Random Battles agent, added only when we explicitly choose one.

This is a staged benchmark harness, not a new Pokémon bot project. The first two players are useful for connection, legality, and simple tactical checks; `SimpleHeuristicsPlayer` is the first meaningful baseline for Jev's strategic decision quality.

For a video, the interface can show a game-like promotion path: a win unlocks the next opponent tier. For an accurate evaluation report, do not promote after only one win. Pokémon battles contain random teams, critical hits, misses, and matchup variance. Instead, run a fixed number of battles per tier and report win rate, confidence interval, latency, timeout/fallback rate, and illegal-action rate.

The resulting evaluation has three separate claims:

- **Reproducible:** Jev completes staged local matches against pinned reference players.
- **Real-world:** Jev can enter public Gen 9 Random Battles and play real opponents.
- **Human comparability:** Jev's public rating and GXE can be compared with the public ladder after enough games; this is not established by a single staged win or single human match.

## Sources

- [TypeSafe/Jev API guide](https://jevtypesafeai.com/how-to-use)
- [TypeSafe announcement of System One and Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- [OpenCode server documentation](https://opencode.ai/docs/server/)
- [OpenCode provider documentation](https://opencode.ai/docs/providers/)
- [Pokémon Showdown protocol](https://github.com/smogon/pokemon-showdown/blob/master/PROTOCOL.md)
- [Pokémon Showdown simulator protocol](https://github.com/smogon/pokemon-showdown/blob/master/sim/SIM-PROTOCOL.md)
- [Pokémon Showdown repository](https://github.com/smogon/pokemon-showdown)
- [Pokémon Showdown ladder help](https://pokemonshowdown.com/pages/ladderhelp)
- [Pokémon Showdown Gen 9 Random Battle ladder](https://pokemonshowdown.com/ladder/gen9randombattle)
- [Pokémon Showdown client web APIs](https://github.com/smogon/pokemon-showdown-client/blob/master/WEB-API.md)
- [poke-env repository](https://github.com/hsahovic/poke-env)
- [poke-env documentation](https://poke-env.readthedocs.io/en/stable/)
- [poke-env battle API](https://poke-env.readthedocs.io/en/stable/modules/battle.html)
- [poke-env player API](https://poke-env.readthedocs.io/en/stable/modules/player.html)
- [poke-env damage calculator API](https://poke-env.readthedocs.io/en/stable/modules/damage_calculator.html)
- [poke-env damage calculator module](https://poke-env.readthedocs.io/en/stable/modules/calc.html)
- [poke-env Pokémon API](https://poke-env.readthedocs.io/en/stable/modules/pokemon.html)
- [poke-env Move API](https://poke-env.readthedocs.io/en/stable/modules/move.html)
