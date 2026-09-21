# Current Pokémon Showdown Harness: System Study

Study date: 2026-09-20  
Scope: the current repository implementation of the Showdown connection, battle-state adapter, decision boundary, order execution, telemetry, and local test harness.

This is a handoff document for future Codex agents. It describes the implementation that exists now, not an ideal redesign. The separate Jev study is in [jev-ai-typesafe-research-2026-09-20.md](jev-ai-typesafe-research-2026-09-20.md).

Existing Markdown files under `docs/research` were not used for this study. This document is based on the current source files, tests, installed `poke-env` 0.16.1 behavior, and the project README inspected during the study.

## Executive summary

The project has two different Showdown paths:

1. **Public/live path:** `poke-env` connects to a real Showdown-compatible WebSocket server, authenticates a Showdown account, searches the Gen 9 Random Battles ladder, parses the real battle protocol, and sends real orders.
2. **Integration-test path:** a small in-process WebSocket stub imitates enough of the protocol to exercise connection, request parsing, Jev calls, order submission, and battle completion. It is not a Pokémon battle simulator.

The current system boundary is:

```text
Showdown WebSocket
    ↓
poke-env PSClient and Battle parser
    ↓
JevPlayer
    ├─ enumerate candidate actions
    ├─ calculate deterministic facts
    ├─ serialize a compact state snapshot
    ├─ call Jev through the System One HTTP client
    ├─ validate the returned candidate ID
    └─ map it to a poke-env BattleOrder
    ↓
poke-env sends /choose
    ↓
Showdown resolves the action
```

Jev never receives a raw Showdown command and never constructs a raw `/choose` string. The project creates the real order object first, then uses Jev only to select one candidate ID.

## 1. Repository map

| File | Responsibility |
| --- | --- |
| `src/jev_showdown/config.py` | Environment settings and local/public server configuration selection |
| `src/jev_showdown/main.py` | CLI plus public matchmaking orchestrator |
| `src/jev_showdown/agent.py` | `JevPlayer`, per-turn loop, raw protocol hooks, lifecycle events |
| `src/jev_showdown/battle/candidates.py` | Candidate move, Tera-move, and switch construction |
| `src/jev_showdown/battle/facts.py` | Type effectiveness and damage/KO annotations |
| `src/jev_showdown/battle/snapshot.py` | Compact state serializer and opponent fog of war |
| `src/jev_showdown/strategy/fallback.py` | Choice validation and deterministic fallback policy |
| `src/jev_showdown/decision/opencode_jev.py` | Direct HTTP client for OpenCode System One |
| `src/jev_showdown/decision/protocol.py` | Local `JevDecisionResponse` dataclass |
| `src/jev_showdown/telemetry/events.py` | Raw protocol event scanner and turn history |
| `src/jev_showdown/telemetry/frames.py` | Bounded raw protocol replay buffer |
| `src/jev_showdown/web/server.py` | FastAPI server, telemetry hub, embedded Showdown renderer proxy |
| `benchmarks/run_matches.py` | Headless matches against `RandomPlayer` or `SimpleHeuristicsPlayer` |
| `tests/integration/test_e2e_battle.py` | Scripted WebSocket test server and full adapter pipeline test |

## 2. Startup and connection flow

The CLI is:

```powershell
python -m jev_showdown.main serve --port 8000
python -m jev_showdown.main benchmark --opponent random --matches 5
```

`serve` creates a FastAPI app and a `BattleOrchestrator`. The browser's `START_BATTLE` WebSocket message triggers `orchestrator.start()`.

`benchmark` creates a `JevPlayer`, a `RandomPlayer` or `SimpleHeuristicsPlayer`, and calls `battle_against`.

The important defaults are:

```text
BATTLE_FORMAT=gen9randombattle
JEV_ENDPOINT=https://opencode.ai/zen/v1/systemone
JEV_MODEL=jev-1.13-free
JEV_TIMEOUT_SECONDS=10.0
```

The Jev contract itself is documented separately in [jev-ai-typesafe-research-2026-09-20.md](jev-ai-typesafe-research-2026-09-20.md).

`server_configuration_for()` maps `localhost` and `127.0.0.1` to `poke-env`'s canned `LocalhostServerConfiguration`. Every other host maps to `poke-env`'s canned `ShowdownServerConfiguration`. The current implementation therefore does not truly support arbitrary remote Showdown-compatible URLs; custom host, port, path, or authentication behavior would need redesign.

### Public flow

`BattleOrchestrator._run()`:

1. refuses to start without Showdown credentials;
2. creates a `JevSystemOneClient`;
3. creates `JevPlayer` with account configuration and telemetry callbacks;
4. waits for the WebSocket and `logged_in` event;
5. publishes connection/auth/search statuses;
6. calls `player.ladder(1)`;
7. waits for `BATTLE_START` or search timeout;
8. lets `poke-env` process the battle;
9. publishes the completed state; and
10. closes the WebSocket and Jev HTTP client.

## 3. Showdown protocol and `poke-env`

The live sequence is approximately:

```text
|challstr|...
    ↓
login / rename
    ↓
|updateuser|...
    ↓
logged_in
    ↓
/search gen9randombattle
    ↓
>battle-...
|init|battle
|player|...
|start
    ↓
|request|{JSON}
    ↓
Battle.parse_request()
    ↓
JevPlayer.choose_move()
```

`poke-env` opens the WebSocket, handles the login challenge, creates a Gen 9 `Battle` object, parses battle messages, and serializes `BattleOrder` objects back into protocol messages.

It parses messages such as `|switch|`, `|move|`, `|-damage|`, `|-status|`, `|-stat|`, `|turn|`, `|faint|`, and `|win|`.

When a request arrives, `poke-env` updates the battle with:

- own team and conditions;
- active Pokémon;
- available moves and switches;
- move PP and disabled state;
- forced-switch state;
- trapping and waiting state;
- Terastallization availability;
- team preview state; and
- the raw last request, including `rqid`.

The base player calls `choose_move()` for ordinary move requests. `JevPlayer` does not override team preview, so non-random formats would still use the base player's team-preview behavior.

## 4. Exact per-turn pipeline

The complete project loop is implemented in `JevPlayer.choose_move()`.

### 4.1 Candidate construction

`build_candidate_actions(battle)` examines `battle.available_moves` and `battle.available_switches`.

For each available move with positive PP it creates an ID like:

```text
move_earthquake
```

If `battle.can_tera` is true, it also creates a Tera variant such as:

```text
move_earthquake_tera
```

For each available switch it creates an ID such as:

```text
switch_rotomwash
```

Each candidate stores:

- an ID;
- kind: `move`, `move_tera`, or `switch`;
- a display label;
- a real `SingleBattleOrder`; and
- deterministic facts.

The candidate builder is project logic. It is not the same representation as `battle.valid_orders`, although it is intended to represent the same current legal choice space.

### 4.2 Deterministic facts

`annotate_candidates_with_facts()` calculates or records:

- base power;
- move type and category;
- accuracy;
- type effectiveness;
- damage range;
- calculation mode and assumptions;
- estimated KO status;
- switch Pokémon species;
- switch HP fraction; and
- switch status.

For ordinary moves it first attempts the `poke-env` Gen 9 calculator. If known identifiers, stats, or HP data are insufficient, it uses a heuristic based mainly on base power and type effectiveness and labels it `heuristic_estimate`.

The human-readable criteria sent to Jev look like:

```text
Earthquake; Power: 100, Type: GROUND, 2.0x effective. Calc Damage: 70-83%
```

or:

```text
Switch to Rotom-Wash; HP: 82%, Status: HEALTHY.
```

### 4.3 State snapshot

`BattleSnapshotSerializer.build_snapshot()` returns:

```text
state_schema
battle_format
turn
weather
fields
side_conditions.self
side_conditions.opponent
can_tera
self.active_pokemon
self.team
opponent.active_pokemon
opponent.team_slots
legal_actions
```

A visible Pokémon may contain:

```text
revealed
species
hp_fraction
hp
max_hp
level
fainted
status
types
boosts
effects
```

The opponent team is always represented as six slots. Revealed Pokémon are serialized; unrevealed slots have no guessed species or hidden details.

Each legal action contains its ID, kind, label, and facts. The raw `BattleOrder` object is not serialized.

### 4.4 Jev request

The project sends one HTTP request per decision through `JevSystemOneClient`:

```json
{
  "model": "jev-1.13-free",
  "state": "serialized battle snapshot",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Choose the strongest legal action that maximizes win probability.",
      "criteria": {
        "move_earthquake": "Earthquake; ...",
        "switch_rotomwash": "Switch to Rotom-Wash; ..."
      }
    }
  }
}
```

This is a direct System One call, not a chat or agent loop.

The expected response contains the model, `answers.action.choice`, confidence, probabilities, usage, and cost. The project maps this into `JevDecisionResponse`.

### 4.5 Validation and order submission

`resolve_order()`:

1. uses fallback if the client reports an error;
2. uses fallback if the choice is missing;
3. uses fallback if the choice is not a current candidate ID; and
4. otherwise returns the candidate's stored `BattleOrder`.

`poke-env` then reads the order's `.message` and sends it to the room. A move becomes a command similar to:

```text
/choose move earthquake
```

Jev does not create or edit this command.

## 5. Fallback policy

The deterministic fallback in `strategy/fallback.py` is:

1. exactly one candidate: use the forced action;
2. otherwise, choose the move with highest `base_power × type_multiplier`;
3. otherwise, choose the first candidate;
4. if candidate construction produced nothing, use the first `battle.valid_orders` item; and
5. if no order is available, use `DefaultBattleOrder` (`/choose default`).

Every fallback includes a reason and is marked `is_fallback=true` in telemetry. This is a safety mechanism, not a claim that the fallback is strategically strong.

## 6. What Jev receives versus telemetry-only data

### Sent to Jev

- compact current-state snapshot;
- visible own and opponent Pokémon information;
- six opponent team slots with unknown slots preserved;
- weather, fields, side conditions, and Tera availability;
- candidate IDs, labels, kinds, and deterministic facts; and
- human-readable Choice criteria.

### Not sent to Jev by the current snapshot

- raw Showdown protocol lines;
- raw `|request|` JSON;
- raw `BattleOrder` objects;
- hidden opponent team information;
- full raw turn transcript;
- recent turn-history tracker;
- previous Jev decisions or conversation history;
- explicit request ID or `rqid`;
- battle timer information;
- every request flag such as `forceSwitch`, `wait`, `trapped`, or `maybeTrapped`;
- all PP and disabled details as explicit snapshot fields; and
- complete priority/speed analysis.

The current state is a lossy projection of the `poke-env` battle object. The detailed Jev boundary is documented in [jev-ai-typesafe-research-2026-09-20.md](jev-ai-typesafe-research-2026-09-20.md).

## 7. Telemetry and dashboard path

Telemetry is separate from decision input.

After each turn, `TURN_DECISION` includes the snapshot, criteria, actual Jev request, parsed Jev response, latency, token usage, validation result, submitted order, fallback status, and recent history. Credential-like response fields are recursively redacted.

`JevPlayer._handle_battle_message()` also observes raw battle frames before delegating to `poke-env`. It forwards frames to the dashboard and feeds them into `BattleEventScanner`.

The scanner tracks moves, switches, damage, status, stat changes, Terastallization, faints, and turn boundaries. It seeds HP baselines from request payloads to estimate observed damage percentages. This scanner is for observability; it is not authoritative battle state and does not feed Jev.

The FastAPI server also proxies/caches an embedded official Showdown renderer. The renderer is visual only; the agent plays through its own `poke-env` WebSocket. At the studied repository state, the static directory contains renderer assets but no full dashboard `index.html`, so the root route falls back to a minimal page when no dashboard shell is present.

## 8. Benchmark and integration-test modes

`benchmarks/run_matches.py` creates a Jev player and either `RandomPlayer` or `SimpleHeuristicsPlayer`, then calls `battle_against`. The benchmark is only as real as the configured Showdown-compatible server. The repository does not ship a complete local Showdown simulator.

`tests/integration/test_e2e_battle.py` contains `LocalShowdownServer`. It:

1. accepts two WebSocket clients;
2. performs simplified login;
3. waits for challenge and accept;
4. sends fixed battle initialization;
5. sends fixed team/request payloads;
6. waits for both `/choose` messages;
7. sends scripted turn markers; and
8. sends a fixed `|win|` at the final scripted turn.

It does **not** calculate damage, enforce real Pokémon legality, simulate speed, apply status effects, model abilities/items, or reproduce Gen 9 Random Battles. Its passing result proves protocol and adapter orchestration, not gameplay correctness or strategic strength.

## 9. Current authority by concern

| Concern | Current authority |
| --- | --- |
| Game rules and final legality | Real Showdown server |
| Protocol connection and parsing | `poke-env` |
| Project action list | `build_candidate_actions()` |
| Project deterministic annotations | `facts.py` |
| Information shown to Jev | `snapshot.py` plus criteria map |
| Jev transport | `opencode_jev.py` |
| Final candidate validation | `fallback.py` / `resolve_order()` |
| Final serialized order | `poke-env` `BattleOrder` |
| Dashboard battle history | `BattleEventScanner` / `TurnHistoryTracker` |
| Local E2E battle result | Scripted test server, not Pokémon mechanics |

When components disagree, the real Showdown server is the final authority on legality and outcome.

## 10. Current limitations and redesign risks

These are observations, not completed fixes.

### Local tests do not validate battle mechanics

The local server is a protocol fixture, not a simulator. A real local Showdown server or another authoritative simulator is needed for mechanics and strength evaluation.

### Candidate enumeration can drift from actual legal orders

The project builds candidates separately from `battle.valid_orders`. This can matter for forced requests, waiting states, unusual target syntax, or future formats.

### Estimated damage units are inconsistent

The exact path converts damage to percentages. The heuristic path uses a base-power/effectiveness estimate but labels the resulting numbers as percentages. Estimated damage and KO status can therefore be misleading in incomplete-information states.

### Jev state omits important request metadata

The snapshot does not explicitly include request IDs, timer information, forced-switch flags, trapping flags, or all move-availability details.

### No explicit stale-request protection

The Jev call is not correlated to an explicit request ID during final validation. A redesign should handle a request changing or ending while the external call is in flight.

### External response validation is lightweight

The client maps JSON into a dataclass but does not fully validate schema, answer type, probability coverage, probability sum, or model-version expectations.

### Timeout/retry policy is incomplete

The current client uses the configured HTTP timeout and falls back on failure. Provider retryable errors and exponential backoff are not fully implemented in the project adapter.

### Public/local server configuration is narrow

The mapper chooses canned `poke-env` server configurations rather than supporting arbitrary host, port, path, and authentication settings.

## 11. Verification evidence

The installed project environment was used to inspect `poke-env` 0.16.1 behavior, including player request handling, `Battle.parse_request()`, `Battle.valid_orders`, login/ladder methods, battle message dispatch, and `SingleBattleOrder` serialization.

The repository test suite was run from its virtual environment:

```text
48 passed, 2 dependency deprecation warnings
```

This verifies the adapter and scripted protocol fixture. It must not be described as proof that a complete local Gen 9 battle simulator is working.

## 12. Compact handoff

1. `poke-env` is the live protocol adapter and battle-object source.
2. Showdown is authoritative for actual legality and game resolution.
3. `JevPlayer.choose_move()` is the decision boundary.
4. The project sends Jev a compact snapshot plus a Choice criteria map.
5. Jev returns a candidate ID, not a Pokémon command.
6. The validator maps that ID to a prebuilt `BattleOrder`.
7. A deterministic fallback handles provider, parsing, or selection failures.
8. Dashboard telemetry and raw protocol scanning are observability paths, not Jev input.
9. The local integration server is scripted and not a complete Pokémon simulator.
10. Read the separate [Jev research document](jev-ai-typesafe-research-2026-09-20.md) before changing the AI request/response contract.

