# Autonomous Pokémon Showdown Agent Powered by Jev AI

A fully autonomous Gen 9 Random Battles agent for [Pokémon Showdown](https://pokemonshowdown.com/).
Every turn, a typed decision model (**Jev 1.13 Free**) receives a structured snapshot of the battle
state plus deterministic, harness-computed criteria, and returns a candidate action. The harness
validates the choice against the legal candidates before executing it — and if Jev fails in any
way, a deterministic fallback takes over, clearly labeled `JEV FAILED — FALLBACK USED`.

A local dashboard streams the observable path from Showdown state through harness calculations,
Jev's actual typed response, adapter validation, submitted order, and observed result. It does not
invent model reasoning or display values that the application/provider did not return.

## Quick start

Requires Python 3.10+.

```powershell
# 1. Create and activate a project-local virtual environment with uv
uv venv .venv --python 3.11
.\.venv\Scripts\Activate.ps1

# 2. Install the agent (src layout) with dev dependencies
uv pip install --python .venv\Scripts\python.exe -e ".[dev]"

# 3. Configure
Copy-Item .env.example .env
#    - SHOWDOWN_USERNAME / SHOWDOWN_PASSWORD: a (dedicated) Showdown account,
#      needed for public matchmaking via the dashboard.
#    - JEV_*: the Jev decision endpoint/model/auth (public defaults are fine).

# 4. Run the dashboard
python -m jev_showdown.main serve --port 8000
```

Open <http://localhost:8000> and press **START JEV BATTLE**. The agent connects to Showdown,
authenticates, queues for a Gen 9 Random Battle opponent, and plays autonomously while the
dashboard narrates every turn.

### Benchmark mode (controlled Showdown server + Jev API)

```powershell
python -m jev_showdown.main benchmark --opponent random --matches 5
python -m jev_showdown.main benchmark --opponent simple_heuristics --matches 10
```

Runs the Jev player against a `RandomPlayer` or `SimpleHeuristicsPlayer` on the
configured Showdown-compatible server and calls the configured Jev endpoint for
each decision. It prints win/loss and turn statistics; it is not an offline or
Jev-free benchmark.

### Tests

```powershell
python -m pytest -v
```

Covers the decision loop, validator/fallback, snapshot serializer, battle-line event scanner,
orchestrator lifecycle, web server/WebSocket hub, and a full end-to-end simulated battle.

## The per-turn decision loop

1. **Legal candidates** — poke_env delivers a battle request; the harness enumerates every legal
   action (usable moves + switches) as typed candidates.
2. **Deterministic criteria** — the harness computes observable facts per candidate (type
   effectiveness, legal switches, KO checks, HP fractions, and either a poke-env Gen 9 damage
   range or a clearly labeled incomplete-information estimate). The model never invents numbers.
3. **State snapshot** — the battle state is serialized for the model, with opponent-team fog of
   war (six closed slots until revealed).
4. **Jev decision** — the model returns a typed choice with confidence and a probability
   distribution over the candidates.
5. **Validation** — the harness resolves the order against the legal candidate set. Any error
   (timeout, malformed choice, illegal candidate, transport failure) resolves to a deterministic
   fallback strategy, attributed to the adapter — never presented as a Jev decision.
6. **Telemetry** — a `TURN_DECISION` event (exact structured request, typed response, choice,
   confidence, probabilities, tokens/cost, validation, submitted order, snapshot, and recent
   history) is broadcast to the dashboard over WebSocket.

### Battle lifecycle

The dashboard's **START JEV BATTLE** button drives an observable, one-battle-at-a-time flow:

`READY → CONNECTING TO SHOWDOWN → AUTHENTICATING → SELECTING GEN 9 RANDOM BATTLE →
SEARCHING FOR OPPONENT → MATCH FOUND — INITIALIZING BATTLE → JEV PLAYING → READY`

Failures surface as clear error states (connection timeout, authentication failure, search
timeout, missing account) instead of a silently stuck button. `BATTLE_START` / `BATTLE_END`
lifecycle events are emitted by the player and forwarded to the dashboard.

### Turn history

The agent scans raw Showdown battle lines (`-move`, `-damage`, `-status`, `-stat`, `-faint`,
`-switch`, turn markers) with HP baselines seeded from `|request|` payloads, so the dashboard's
turn timeline shows real outcomes: damage percentages against true max HP, status conditions,
stat-stage badges, switches, and faints — for both Jev's moves and the opponent's.

## Configuration (`.env`)

| Variable | Default | Description |
| --- | --- | --- |
| `SHOWDOWN_USERNAME` | — | Showdown account username (required for dashboard matchmaking). |
| `SHOWDOWN_PASSWORD` | — | Showdown account password (required for dashboard matchmaking). |
| `SHOWDOWN_SERVER_URL` | `sim3.psim.us:8000` | Showdown server host. `localhost` / `127.0.0.1` targets a local Showdown-compatible server (used by the tests); any other host connects to the public Showdown server. |
| `JEV_ENDPOINT` | `https://opencode.ai/zen/v1/systemone` | Jev decision endpoint. |
| `JEV_MODEL` | `jev-1.13-free` | Jev model identifier. |
| `JEV_AUTH_TOKEN` | `Bearer public` | Auth token (a bare token is auto-prefixed with `Bearer `). |
| `JEV_TIMEOUT_SECONDS` | `10.0` | Per-decision timeout; expiry triggers the labeled fallback. |
| `BATTLE_FORMAT` | `gen9randombattle` | Target format. |
| `DASHBOARD_PORT` | `8000` | Dashboard web server port. |

> Secrets are never displayed on the dashboard or included in telemetry.

## Project layout

```
src/jev_showdown/
├── agent.py            # JevPlayer: per-turn decision loop + battle lifecycle hooks
├── main.py             # CLI (serve/benchmark) + BattleOrchestrator (public matchmaking flow)
├── config.py           # Settings / .env loading
├── battle/
│   ├── candidates.py   # Legal candidate enumeration (moves + switches)
│   ├── facts.py        # Deterministic criteria (damage, type match, KO)
│   ├── snapshot.py     # State snapshot serializer (fog of war)
│   └── validator.py    # Jev output validation + resolved battle order
├── decision/
│   ├── opencode_jev.py # Jev decision client (direct typed endpoint call)
│   └── protocol.py     # Typed JevDecisionResponse
├── strategy/fallback.py# Deterministic fallback ladder
├── telemetry/events.py # Turn history tracker + raw battle-line event scanner
└── web/
    ├── server.py       # FastAPI app + WebSocket hub (thread-safe publish)
    └── static/         # Official renderer assets; dashboard shell is intentionally absent
benchmarks/             # Local reproducible benchmark harness
tests/                  # Unit + end-to-end integration tests
docs/                   # Alignment record, design docs, research logs, plan
```

## Design docs

- [Project alignment record](docs/project-alignment.md) — product direction and constraints.
- [Dashboard product contract](docs/design/dashboard-product-contract.md) — authoritative dashboard behavior and creative boundary.
- [Dashboard Codex handoff](docs/design/dashboard-codex-handoff.md) — implementation handoff.
- [Phase 0 research](docs/research/phase-0-jev-opencode.md) · [Phase 1 research](docs/research/phase-1-research-and-architecture.md)

## Attribution

- **Pokémon Showdown** battle protocol and ladder: [pokemonshowdown.com](https://pokemonshowdown.com/),
  [poke-env](https://github.com/PokeEngines/poke-env) (MIT).
- **Pokémon sprite art**: animated front/back battle sprites served from the official
  [Pokémon Showdown sprite directory](https://play.pokemonshowdown.com/sprites/xyani/) and
  [Smogon sprite repository](https://github.com/smogon/sprites), used by the custom dashboard
  renderer without embedding the full Showdown client UI.
  Pokémon and Pokémon character names are trademarks of Nintendo / The Pokémon Company; this
  project is a fan-made research tool and is not affiliated with or endorsed by them.
## Important constraint

Jev is a typed decision model: the agent calls its decision endpoint directly (structured
request/response with a timeout) and does **not** route Jev through any chat/agent loop.
