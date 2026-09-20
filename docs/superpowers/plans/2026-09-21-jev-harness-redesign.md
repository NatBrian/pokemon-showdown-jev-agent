# Jev Pokemon Harness and Decision-System Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Rebuild the Gen 9 Random Battle decision boundary so Jev receives authoritative, uncertainty-labelled move and switch consequences and returns one validated legal action within the Showdown timer.

**Architecture:** Keep poke-env and the real Showdown server authoritative for battle state, legality, and outcomes. Refactor the current per-turn pipeline around typed request metadata, a registry derived from battle.valid_orders, provenance-labelled facts, conservative hidden-information/response summaries, a compact Jev Choice request, freshness validation, and a deterministic fallback. Add replayable decision telemetry and no-cost local evaluation support, while keeping Foul Play as an external benchmark rather than porting its search into the live path.

**Tech Stack:** Python 3.10+, poke-env>=0.16.1,<0.17, httpx>=0.27.0,<0.28, pydantic>=2,<3, pytest>=8,<10, pytest-asyncio>=0.23,<2, existing JevSystemOneClient, FastAPI telemetry, and the installed poke-env Gen 9 calculator.

**Spec:** docs/jev-harness-redesign-design-2026-09-21.md

## Global Constraints

- **Target format:** Gen 9 Random Battle singles (gen9randombattle); do not silently generalize the first implementation to VGC, doubles, or unrelated formats.
- **Showdown is authoritative:** the real Showdown battle engine is the final authority for legality and outcomes; poke-env is the protocol and battle-object adapter.
- **One live Jev decision per request:** one typed Choice request is allowed for each current decision request; no serial debate loop, per-action Jev calls, or live MCTS.
- **Wrong information:** every derived fact must carry a source, unit or representation, confidence/probability when meaningful, and assumptions; unknown information remains unknown.
- **Overfitting:** expose all current legal actions; never remove an action because a local heuristic dislikes it; provide consequences and hypotheses rather than a hard-coded final verdict.
- **Latency:** keep local decision preparation bounded, use the configured Jev timeout/deadline, reject stale responses, and make the fallback available before the external request completes.
- **Mechanics honesty:** heuristic estimates must not be labelled exact damage, damage percentage, KO probability, or win probability; approximate simulators stay offline/shadow until differential parity is demonstrated.
- **Action safety:** Jev returns a candidate ID only; the application maps that ID to a stored BattleOrder and validates it against the current request before submission.
- **No PokeChamp evaluation:** do not spend paid LLM calls evaluating PokeChamp; the external strong-bot benchmark in this plan is Foul Play only.
- **No cost-control subsystem:** do not add API budget managers, quota systems, billing logic, or cost dashboards. During implementation, use no Jev calls for local tests, one call per live decision, and no extra shadow Jev call by default.
- **No wholesale bot port:** do not port Foul Play MCTS, poke-engine, PokéChamp LocalSim, or a large hand-written Pokemon playbook into the live agent.
- **Existing foundation:** preserve the current Showdown connection, JevPlayer, BattleOrder flow, dashboard lifecycle, and public configuration unless a change is required by the new decision contract.

## Review Focus

These are the five failure classes most likely to escape ordinary happy-path tests. Each is assigned to the task that owns the behavior.

1. **Forced-switch, trapped, wait, and missing-request cases:** the action registry must exactly reflect the current battle.valid_orders, including a protocol-safe default order when Showdown says to wait. Test in Task 2.
2. **Random Battle fog of war:** revealed bench, unknown slot, fainted slot, and revealed species with unknown set details must remain distinct; no hidden move, item, ability, or species may be silently invented. Test in Task 4 and Task 5.
3. **Tera, duplicate names, and order mapping:** normal moves, Tera moves, switches, duplicate display names, and target/order variants must retain unique IDs that map to the exact stored BattleOrder. Test in Task 2 and Task 7.
4. **Stale or malformed Jev responses:** a response for an old rqid, turn, state version, or candidate set must never be submitted; malformed Choice probabilities must fall back safely. Test in Task 6 and Task 7.
5. **Incomplete mechanics:** exact calculator output and heuristic estimates must use different fields and units; an incomplete Random Battle state must not produce a fake exact percentage or KO claim. Test in Task 3 and Task 9.

## File Map

| File | Responsibility after redesign |
| --- | --- |
| Create src/jev_showdown/battle/contracts.py | JSON-safe provenance, request metadata, decision fingerprint, and fact contracts shared by the live pipeline. |
| Create src/jev_showdown/battle/state.py | Extract request metadata and current state version from poke-env without becoming a second battle parser. |
| Create src/jev_showdown/battle/beliefs.py | Preserve observed versus inferred versus unknown opponent information and expose a conservative hidden-information ledger. |
| Create src/jev_showdown/battle/consequences.py | Build bounded, labelled action-response summaries for moves and switches; never choose the final action. |
| Modify src/jev_showdown/battle/candidates.py | Build the legal action registry from battle.valid_orders and retain exact stored BattleOrder objects. |
| Modify src/jev_showdown/battle/facts.py | Emit unit-safe fact records and stop treating heuristic damage as exact percentage damage. |
| Modify src/jev_showdown/battle/snapshot.py | Serialize schema version 2 decision context with request metadata, history, beliefs, responses, and all legal actions. |
| Modify src/jev_showdown/decision/protocol.py | Represent validated Jev responses and request fingerprints. |
| Modify src/jev_showdown/decision/opencode_jev.py | Keep one typed Choice call and validate the provider response without an in-turn retry loop. |
| Modify src/jev_showdown/strategy/fallback.py | Implement the verified-fact fallback ladder and current-request legality checks. |
| Modify src/jev_showdown/agent.py | Orchestrate the new pipeline, track state versions, reject stale responses, and record replayable decision packages. |
| Modify src/jev_showdown/telemetry/events.py | Keep protocol scanning observational and attach authoritative decision-package metadata to history events. |
| Create benchmarks/replay_decisions.py | Read/write saved decision packages for repeatable no-provider replay and context inspection. |
| Create benchmarks/evaluation.py | Summarize battle outcomes, fallbacks, illegal/stale results, and latency without adding billing or budget control. |
| Modify benchmarks/run_matches.py | Preserve local RandomPlayer/SimpleHeuristicsPlayer gates and emit reproducible benchmark metadata. |
| Modify tests listed in each task | Pin each contract and failure mode without making provider calls. |

## Shared Interfaces

The following names and shapes are the boundaries that later tasks must preserve. They are JSON-friendly because the state is sent to Jev and recorded for replay.

~~~python
from dataclasses import dataclass
from typing import Any, Literal

FactSource = Literal["observed", "calculated", "inferred", "unknown"]

@dataclass(frozen=True)
class Fact:
    value: Any
    source: FactSource
    unit: str | None = None
    confidence: float | None = None
    assumptions: tuple[str, ...] = ()

@dataclass(frozen=True)
class BattleRequestMetadata:
    battle_id: str | None
    request_id: str | int | None
    state_version: int
    turn: int
    request_type: Literal["move", "switch", "wait", "team_preview", "unknown"]
    force_switch: bool
    wait: bool
    trapped: bool
    maybe_trapped: bool
    deadline_monotonic: float | None

@dataclass(frozen=True)
class DecisionFingerprint:
    battle_id: str | None
    request_id: str | int | None
    state_version: int
    turn: int
    candidate_ids: tuple[str, ...]

def extract_request_metadata(
    battle: AbstractBattle,
    *,
    state_version: int,
    deadline_monotonic: float | None = None,
) -> BattleRequestMetadata:
    pass

def build_decision_fingerprint(
    metadata: BattleRequestMetadata,
    candidate_ids: tuple[str, ...],
) -> DecisionFingerprint:
    pass

def build_candidate_actions(
    battle: AbstractBattle,
) -> dict[str, CandidateAction]:
    pass

def annotate_candidates_with_facts(
    battle: AbstractBattle,
    candidates: dict[str, CandidateAction],
) -> dict[str, str]:
    pass

def build_snapshot(
    battle: AbstractBattle,
    candidates: dict[str, CandidateAction],
    *,
    metadata: BattleRequestMetadata,
    criteria: dict[str, str],
    recent_history: list[dict[str, Any]],
    beliefs: dict[str, Any],
    consequences: dict[str, Any],
) -> dict[str, Any]:
    pass

def resolve_order(
    jev_res: JevDecisionResponse,
    candidates: dict[str, CandidateAction],
    battle: AbstractBattle,
    *,
    expected_fingerprint: DecisionFingerprint,
    current_fingerprint: DecisionFingerprint,
) -> ValidatedOrder:
    pass
~~~

The pass bodies in this interface listing are signatures only. Implementation tasks must provide complete function bodies and tests. No task may introduce a second incompatible representation for the same boundary.

## Task 1: Establish Shared Contracts and Request Metadata

**Files:**
- Create: src/jev_showdown/battle/contracts.py
- Create: src/jev_showdown/battle/state.py
- Create: tests/unit/test_contracts.py
- Create: tests/unit/test_state.py

**Interfaces:**
- Consumes: poke_env.battle.AbstractBattle, battle.last_request, battle.turn, battle.battle_tag, and request flags exposed by poke-env.
- Produces: Fact, BattleRequestMetadata, DecisionFingerprint, extract_request_metadata(), and build_decision_fingerprint() for Tasks 2–7.

- [ ] **Step 1: Write failing contract tests.**

Construct small MagicMock battles and verify normal move, forced switch, wait, missing rqid, and absent battle tag cases. Use:

~~~python
metadata = extract_request_metadata(
    battle,
    state_version=4,
    deadline_monotonic=123.0,
)
assert metadata.request_id == "req-4"
assert metadata.request_type == "move"
assert metadata.force_switch is False
assert metadata.wait is False
assert metadata.state_version == 4

fingerprint = build_decision_fingerprint(metadata, ("move_a", "switch_b"))
assert fingerprint.candidate_ids == ("move_a", "switch_b")
~~~

Missing fields must become None, False, or "unknown"; they must not raise or invent an ID.

- [ ] **Step 2: Run the focused tests and verify they fail.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_contracts.py tests/unit/test_state.py -q
~~~

Expected: collection or attribute failures because the new modules and extraction functions do not exist.

- [ ] **Step 3: Implement the JSON-safe contracts.**

In contracts.py, validate Fact.confidence only when present and require it to be within [0.0, 1.0]. Add to_dict() that emits value, source, unit, confidence, and assumptions, preserving None for unknown values.

In state.py, read battle.last_request defensively. Derive request_type in this order: wait when battle.wait is true, switch when battle.force_switch is true, move when an active request contains an action list, team_preview when preview data exists, and unknown otherwise. Read rqid without converting its type and use battle.battle_tag as battle_id when present.

- [ ] **Step 4: Run the focused tests and verify they pass.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_contracts.py tests/unit/test_state.py -q
~~~

Expected: all contract and metadata tests pass.

- [ ] **Step 5: Commit the contract boundary.**

~~~powershell
git add src/jev_showdown/battle/contracts.py src/jev_showdown/battle/state.py tests/unit/test_contracts.py tests/unit/test_state.py
git commit -m "refactor: add typed battle decision contracts"
~~~

## Task 2: Rebuild the Legal Action Registry from Showdown Orders

**Files:**
- Modify: src/jev_showdown/battle/candidates.py
- Modify: tests/unit/test_candidates.py

**Interfaces:**
- Consumes: AbstractBattle.valid_orders returning SingleBattleOrder or DefaultBattleOrder objects.
- Produces: an updated CandidateAction and build_candidate_actions(battle) whose stored orders are exactly the orders that the current battle can submit.

- [ ] **Step 1: Write failing legal-parity tests.**

Build battle doubles with explicit valid_orders and assert the candidate registry preserves every order message:

~~~python
orders = [
    SingleBattleOrder(move),
    SingleBattleOrder(switch),
    SingleBattleOrder(move, terastallize=True),
]
battle.valid_orders = orders

candidates = build_candidate_actions(battle)
assert [candidate.order_ref.message for candidate in candidates.values()] == [
    order.message for order in orders
]
~~~

Add tests for force_switch=True with only switch orders, wait=True with DefaultBattleOrder, duplicate move/species IDs, and a legal Tera order. Assert that the registry never adds a Tera action unless that exact Tera order is in battle.valid_orders.

- [ ] **Step 2: Run candidate tests and verify the old implementation fails.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_candidates.py -q
~~~

Expected: parity and wait tests fail because the current code enumerates available moves/switches independently and does not represent DefaultBattleOrder.

- [ ] **Step 3: Implement order-driven candidate construction.**

Refactor build_candidate_actions() to iterate battle.valid_orders exactly once. Inspect each SingleBattleOrder to classify its underlying Move or Pokemon, detect terastallize, and preserve the original order object. Represent a DefaultBattleOrder as kind="default" so the candidate list remains complete for a wait request.

Keep stable ID styles where possible (move_<id>, move_<id>_tera, switch_<species>), disambiguate duplicates deterministically, and keep the stored order_ref as the only source used for submission. Do not add strategic scores in this module.

- [ ] **Step 4: Run candidate tests and inspect order parity.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_candidates.py -q
~~~

Expected: all candidate tests pass, including exact order-message parity, forced-switch, wait, duplicate, and Tera cases.

- [ ] **Step 5: Commit the legal registry.**

~~~powershell
git add src/jev_showdown/battle/candidates.py tests/unit/test_candidates.py
git commit -m "refactor: derive Jev actions from legal battle orders"
~~~

## Task 3: Make Mechanics Facts Unit-Safe and Source-Labelled

**Files:**
- Modify: src/jev_showdown/battle/facts.py
- Modify: tests/unit/test_facts.py

**Interfaces:**
- Consumes: CandidateAction from Task 2 and the installed poke-env Gen 9 calculator.
- Produces: the existing annotate_candidates_with_facts(battle, candidates) function with nested fact records that distinguish calculated, inferred, and unknown values and a criteria map that explains those distinctions to Jev.

- [ ] **Step 1: Write failing fact-contract tests.**

Add assertions for exact and heuristic paths:

~~~python
assert candidate.facts["damage"]["unit"] == "percent_of_target_max_hp"
assert candidate.facts["damage"]["source"] == "calculated"
assert candidate.facts["damage"]["value"] == [50, 60]

assert estimated["damage"]["unit"] == "heuristic_relative_score"
assert estimated["damage"]["source"] == "inferred"
assert estimated["ko"]["value"] is None
~~~

Also test type immunities (0.0), dual-type multipliers, move accuracy/priority/PP, and switches with HP/status plus explicit unknown consequence fields when opponent coverage cannot be calculated.

- [ ] **Step 2: Run facts tests and verify the old implementation fails.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_facts.py -q
~~~

Expected: failures because the current code stores bare numeric estimated ranges and labels heuristic values as percentage damage.

- [ ] **Step 3: Implement the exact-versus-estimate split.**

Keep _exact_damage_percent() limited to poke-env-verified move calculations with known identifiers, maximum HP, and supported non-Tera state. Store exact ranges under a damage fact with unit percent_of_target_max_hp, source calculated, assumptions, and a separate exact KO fact.

For incomplete states, store a bounded heuristic under utility_estimate with unit heuristic_relative_score, source inferred, and explicit assumptions. Set ko.value to None on this path. Never append a percent sign to a heuristic score. Keep base_power * type_multiplier out of any field named damage, KO, survival, or win probability.

- [ ] **Step 4: Update criteria text to preserve meaning.**

Use criteria such as:

~~~text
Earthquake; legal move; type effectiveness 2.0x; calculated damage 50-60% of target max HP; KO=false; accuracy=100%; PP=9.
~~~

For an estimate, say heuristic relative estimate and include unknown assumptions. For a switch, include incoming HP/status and entry_hazard_damage=unknown when no verified calculation exists.

- [ ] **Step 5: Run focused and full tests.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_facts.py tests/unit/test_candidates.py -q
.\\.venv\\Scripts\\python.exe -m pytest -q
~~~

Expected: focused and existing tests pass after assertions are updated for the new fact shape.

- [ ] **Step 6: Commit the fact boundary.**

~~~powershell
git add src/jev_showdown/battle/facts.py tests/unit/test_facts.py
git commit -m "refactor: label battle facts with units and provenance"
~~~

## Task 4: Add Conservative Hidden-Information and Response Summaries

**Files:**
- Create: src/jev_showdown/battle/beliefs.py
- Create: src/jev_showdown/battle/consequences.py
- Create: tests/unit/test_beliefs_and_consequences.py

**Interfaces:**
- Consumes: AbstractBattle, current candidates, current facts, and recent observed events from Tasks 2–3.
- Produces: build_hidden_information_ledger(battle) -> dict[str, Any] and compile_action_responses(battle, candidates, beliefs) -> dict[str, Any].

- [ ] **Step 1: Write failing fog-of-war tests.**

Use a six-slot opponent team with one active, one revealed bench, one fainted revealed Pokemon, and three unknown slots. Verify:

~~~python
assert slots[0]["visibility"] == "revealed_active"
assert slots[1]["visibility"] == "revealed_bench"
assert slots[2]["visibility"] == "fainted"
assert slots[3]["visibility"] == "unknown_slot"
assert slots[0]["moves"][0]["source"] == "observed"
assert slots[0]["unrevealed_set_details"]["source"] == "unknown"
~~~

An unknown species must never serialize as a guessed species or average Pokemon.

- [ ] **Step 2: Add response-summary tests for move, switch, and unknown buckets.**

For each legal action, assert action ID, response categories, source labels, and consequences:

~~~python
assert response["opponent_stays"]["source"] in {"calculated", "unknown"}
assert "opponent_switches_revealed" in response
assert "opponent_switches_unknown" in response
assert response["opponent_switches_unknown"]["probability"] is None
~~~

Add a double-switch fixture and verify that our incoming switch and the opponent's possible incoming switch remain separate.

- [ ] **Step 3: Implement the observed-information ledger.**

Create JSON-safe entries for six opponent slots. Record observed species, forme, HP, status, boosts/effects, revealed moves, item/ability/Tera evidence, and last-seen turn. Represent candidate hidden fields as source=unknown until a trusted evidence provider exists. Evidence entries contain a source and confidence only when the code has an actual basis for it.

Do not add a speculative Randbats dataset or Bayesian predictor in this task. Expose possible_hypotheses and unknown_residual so a later trusted format-data provider can be added without changing Jev's schema.

- [ ] **Step 4: Implement the bounded response compiler.**

Compile opponent_stays, opponent_uses_known_move, opponent_uses_unknown_move, opponent_sets_up_or_statuses, opponent_switches_revealed, and opponent_switches_unknown. Use exact facts from Task 3 when available; otherwise emit value=None, source=unknown, and explicit assumptions. Include switch-in HP/status/hazard fields and a double_switch consequence object for switch candidates.

The compiler must not choose a response, assign a fabricated probability, or produce a single action score. The unknown bucket retains its uncertainty instead of being treated as an average opponent.

- [ ] **Step 5: Run focused tests.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_beliefs_and_consequences.py -q
~~~

Expected: all visibility, unknown-information, response-category, and double-switch tests pass.

- [ ] **Step 6: Commit the uncertainty boundary.**

~~~powershell
git add src/jev_showdown/battle/beliefs.py src/jev_showdown/battle/consequences.py tests/unit/test_beliefs_and_consequences.py
git commit -m "feat: represent hidden information and opponent responses"
~~~

## Task 5: Build the Versioned Jev Decision Context

**Files:**
- Modify: src/jev_showdown/battle/snapshot.py
- Modify: tests/unit/test_snapshot_and_telemetry.py

**Interfaces:**
- Consumes: metadata from Task 1, candidates/facts from Tasks 2–3, beliefs/responses from Task 4, and recent events from TurnHistoryTracker.
- Produces: BattleSnapshotSerializer.build_snapshot(...) -> dict[str, Any] with state_schema=2 and a compact self-describing state for Jev.

- [ ] **Step 1: Write failing schema and history tests.**

Assert:

~~~python
assert state["state_schema"] == 2
assert state["request"]["rqid"] == "req-4"
assert state["request"]["force_switch"] is False
assert state["request"]["state_version"] == 4
assert state["history"][-1]["action"] == "Earthquake"
assert "beliefs" in state
assert "opponent_responses" in state
assert state["glossary"]["switch"]
~~~

Also assert own active move PP/disabled details, side conditions, weather/terrain/fields, Tera state, all six opponent visibility states, all legal candidates, criteria, and deadline metadata are present. No BattleOrder object or secret appears in state.

- [ ] **Step 2: Implement schema version 2 serialization.**

Keep BattleSnapshotSerializer as the public entry point and extend its signature with keyword-only metadata, criteria, recent history, beliefs, and consequences. Preserve the current self/team/opponent layout where possible to avoid unnecessary dashboard breakage.

Use Fact.to_dict() for labelled facts. Add a short generic glossary for switch, setup, status, hazard, priority, safe action, risky prediction, win condition, and lose condition. Definitions must explain meaning without naming a preferred action.

Include only evidence-backed strategic hypotheses: current phase, possible win plans, lose-condition threats, resource criticality, best/likely/worst outcomes, and information each action may reveal. Unsupported hypotheses remain unknown.

- [ ] **Step 3: Keep the context compact and deterministic.**

Sort action IDs and dictionary keys where order is not semantically meaningful. Limit history to the existing recent-event window. Do not add a full transcript, raw protocol lines, full hidden team data, or a multi-turn search tree to the live Jev state.

- [ ] **Step 4: Run snapshot and telemetry tests.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_snapshot_and_telemetry.py -q
~~~

Expected: all observable-state tests pass with schema-version assertions updated from 1 to 2, plus new request/history/belief/response assertions.

- [ ] **Step 5: Commit the Jev context schema.**

~~~powershell
git add src/jev_showdown/battle/snapshot.py tests/unit/test_snapshot_and_telemetry.py
git commit -m "feat: serialize versioned Jev battle context"
~~~

## Task 6: Harden the Jev Choice Gateway and Freshness Contract

**Files:**
- Modify: src/jev_showdown/decision/protocol.py
- Modify: src/jev_showdown/decision/opencode_jev.py
- Create: tests/unit/test_decision_gateway.py
- Modify: tests/unit/test_jev_client.py

**Interfaces:**
- Consumes: schema-versioned state and criteria from Task 5 plus DecisionFingerprint from Task 1.
- Produces: the existing JevSystemOneClient.evaluate_decision(state, criteria, instructions) response shape, with strict validation and no in-turn retry; JevDecisionResponse remains the transport object used by Task 7.

- [ ] **Step 1: Write failing provider-response tests.**

Test this valid shape:

~~~python
valid = {
    "model": "jev-1.13.0",
    "answers": {"action": {
        "type": "choice",
        "choice": "move_a",
        "confidence": 0.8,
        "probabilities": {"move_a": 0.8, "switch_b": 0.2},
    }},
    "usage": {"input_tokens": 100, "output_tokens": 20},
}
~~~

Also test invalid answer type, missing choice, choice outside criteria, non-numeric probabilities, values outside [0, 1], and a probability sum outside a small tolerance. Assert an HTTP error and timeout make one HTTP call and do not trigger an automatic second call.

- [ ] **Step 2: Run gateway tests and verify current gaps fail.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_jev_client.py tests/unit/test_decision_gateway.py -q
~~~

Expected: malformed response tests fail because the current client trusts fields after response.json() and does not validate the Choice distribution.

- [ ] **Step 3: Implement response validation without a retry loop.**

Validate HTTP 200, answers.action.type == choice, string choice, finite confidence in [0, 1], finite probabilities in [0, 1], and a sum within 1e-6 when probabilities are supplied. Require every criteria ID to be represented in the returned probability map when the provider returns a map. Preserve the raw response for diagnostics after telemetry redaction.

Keep JevSystemOneClient.evaluate_decision() as one POST call. When a remaining deadline is supplied, use the smaller of it and the configured timeout. Return an error response on 429/529 instead of retrying inside the battle decision.

- [ ] **Step 4: Run gateway tests and the full unit suite.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_jev_client.py tests/unit/test_decision_gateway.py -q
.\\.venv\\Scripts\\python.exe -m pytest -q
~~~

Expected: focused and existing tests pass, and the client call-count assertion remains exactly one for each evaluation.

- [ ] **Step 5: Commit the gateway contract.**

~~~powershell
git add src/jev_showdown/decision/protocol.py src/jev_showdown/decision/opencode_jev.py tests/unit/test_decision_gateway.py tests/unit/test_jev_client.py
git commit -m "refactor: validate Jev Choice responses"
~~~

## Task 7: Integrate the Live Pipeline, Freshness Gate, and Fallback

**Files:**
- Modify: src/jev_showdown/agent.py
- Modify: src/jev_showdown/strategy/fallback.py
- Modify: src/jev_showdown/battle/validator.py
- Modify: tests/unit/test_validator_and_fallback.py
- Modify: tests/unit/test_agent.py

**Interfaces:**
- Consumes: all contracts from Tasks 1–6.
- Produces: JevPlayer.choose_move() with one Jev call, current-request validation, recorded fingerprints, and ValidatedOrder from the same candidate registry.

- [ ] **Step 1: Write failing fallback and stale-response tests.**

Add tests that verify a response for an old request becomes fallback:

~~~python
stale = resolve_order(
    response,
    candidates,
    battle,
    expected_fingerprint=fingerprint_for_request_4,
    current_fingerprint=fingerprint_for_request_5,
)
assert stale.is_fallback is True
assert "stale" in stale.fallback_reason.lower()
~~~

Add fallback tests for one forced legal order, an exact calculated guaranteed KO, a known immediate-loss consequence, a preserve-only-check annotation, no trustworthy fact, and no candidates with/without a battle.valid_orders order. Heuristic relative estimates must not win solely because their number is large.

- [ ] **Step 2: Implement the fallback ladder using verified fields only.**

Update select_deterministic_fallback() in this order:

1. Use the single legal action.
2. Use an exact calculated guaranteed KO whose accuracy and target state are represented.
3. Avoid a candidate marked by verified consequences as an immediate known loss.
4. Preserve a resource marked as the only known answer to a major threat.
5. Use the highest verified continuation classification when one exists.
6. Use the first current legal candidate.
7. Use battle.valid_orders[0] or DefaultBattleOrder only when the registry is empty.

If no trustworthy field supports priorities 2–5, fall through to the current legal action rather than scoring a heuristic estimate. Do not add a broad Pokemon ruleset to the fallback.

- [ ] **Step 3: Integrate the canonical pipeline in JevPlayer.choose_move().**

For each call, increment a per-battle state version, extract request metadata, build candidates from battle.valid_orders, annotate facts, build beliefs and response summaries, serialize the schema-versioned snapshot, and call evaluate_decision() once. Capture the pre-call DecisionFingerprint.

After the response, extract metadata and candidates again, build a current fingerprint, and pass both fingerprints to resolve_order(). If request ID, battle ID, state version, turn, or candidate IDs differ, return the fallback and mark the reason stale. Do not submit an old BattleOrder.

- [ ] **Step 4: Update telemetry without making scanners authoritative.**

Extend TURN_DECISION with state_schema, request, fingerprint, beliefs, opponent_responses, criteria, jev_response, and the submitted order. Keep BattleEventScanner and TurnHistoryTracker observational; the canonical poke-env battle object remains the state authority.

- [ ] **Step 5: Run agent, fallback, integration, and full tests.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_validator_and_fallback.py tests/unit/test_agent.py -q
.\\.venv\\Scripts\\python.exe -m pytest tests/integration/test_e2e_battle.py -q
.\\.venv\\Scripts\\python.exe -m pytest -q
~~~

Expected: all tests pass; the scripted server still verifies connection/orchestration only, while stale, malformed, forced, and illegal decisions resolve through the safe path.

- [ ] **Step 6: Commit the live decision pipeline.**

~~~powershell
git add src/jev_showdown/agent.py src/jev_showdown/strategy/fallback.py src/jev_showdown/battle/validator.py tests/unit/test_validator_and_fallback.py tests/unit/test_agent.py tests/integration/test_e2e_battle.py
git commit -m "feat: integrate validated Jev battle decision pipeline"
~~~

## Task 8: Add Replayable Decision Packages and Local Evaluation Metrics

**Files:**
- Create: benchmarks/replay_decisions.py
- Create: benchmarks/evaluation.py
- Modify: benchmarks/run_matches.py
- Create: tests/unit/test_replay_evaluation.py

**Interfaces:**
- Consumes: TURN_DECISION and BATTLE_END event dictionaries emitted by Task 7.
- Produces: replay helpers and local metrics; it must not call Jev or implement an API budget/quota system.

- [ ] **Step 1: Write failing replay round-trip tests.**

Define JSON Lines helpers:

~~~python
def write_decision_package(path: Path, event: Mapping[str, Any]) -> None:
    pass

def read_decision_packages(path: Path) -> Iterator[dict[str, Any]]:
    pass
~~~

Test that a schema-versioned decision event containing candidate facts, beliefs, criteria, fingerprint, Jev response, fallback, and submitted order can be written and read back with the same JSON values. Malformed JSON lines must be rejected with a line-numbered ValueError, not silently dropped.

- [ ] **Step 2: Write failing evaluation-metric tests.**

Define:

~~~python
@dataclass
class SeriesMetrics:
    battles: int
    wins: int
    losses: int
    draws: int
    decisions: int
    fallbacks: int
    illegal_actions: int
    stale_responses: int
    decision_latencies_ms: list[float]

def summarize_series(events: Iterable[Mapping[str, Any]]) -> SeriesMetrics:
    pass
~~~

Test wins/losses/draws, fallback/stale/illegal counts, and p50/p95/p99 latency helpers. Do not add cost enforcement, billing calculations, or automatic Jev requests.

- [ ] **Step 3: Implement replay serialization and metrics.**

Use UTF-8 JSON Lines with one event per line. Preserve raw probability maps and fact provenance as data. summarize_series() must count only fields recorded by the live player and must never infer mechanics correctness from the scripted local server.

- [ ] **Step 4: Make the existing local benchmark reproducible.**

Update benchmarks/run_matches.py to return or print format, opponent type, match count, wins/losses, fallback count, illegal/stale counts, and latency summary. Keep RandomPlayer and SimpleHeuristicsPlayer as no-cost gates. Do not add PokeChamp and do not create a paid shadow-battle mode.

- [ ] **Step 5: Run evaluation and full tests.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_replay_evaluation.py tests/unit/test_cli_and_benchmark.py -q
.\\.venv\\Scripts\\python.exe -m pytest -q
~~~

Expected: replay and metric tests pass, the existing CLI remains compatible, and no test makes a provider request.

- [ ] **Step 6: Commit replay and evaluation support.**

~~~powershell
git add benchmarks/replay_decisions.py benchmarks/evaluation.py benchmarks/run_matches.py tests/unit/test_replay_evaluation.py
git commit -m "feat: add replayable battle decision evaluation"
~~~

## Task 9: Add Mechanics-Oriented Fixtures and Complete Verification

**Files:**
- Create: tests/fixtures/mechanics_cases.json
- Create: tests/unit/test_mechanics_fixtures.py
- Modify: tests/integration/test_e2e_battle.py

**Interfaces:**
- Consumes: the verified fact shape from Task 3 and the full live pipeline from Task 7.
- Produces: fixture-backed regression coverage that distinguishes protocol orchestration from mechanics correctness.

- [ ] **Step 1: Create small authoritative fixture cases.**

Store JSON cases for a type immunity, a dual-type 4x interaction, a known exact damage range, a hazard switch-in, a status effect, a forced-switch request, a wait request, and a Tera move. Each fixture must include format, observed inputs, expected fact values, units, source classification, and assumptions. Do not claim a local scripted WebSocket result is a mechanics oracle.

- [ ] **Step 2: Write fixture tests before wiring them into the implementation.**

For each fixture, assert the expected fact field and unit. Add a negative assertion that an incomplete opponent state produces source=unknown or source=inferred rather than the exact-calculated classification.

- [ ] **Step 3: Implement fixture loading and comparison.**

Load the fixture file through a small test helper, construct only the required poke-env/move objects, and compare normalized JSON-safe facts. Keep unsupported mechanics explicitly marked unavailable instead of weakening the assertion.

- [ ] **Step 4: Strengthen the end-to-end stub assertions.**

Update test_e2e_battle.py to assert that the agent sends only an ID mapped from the current candidate registry, includes request metadata in telemetry, and never calls a real Jev provider. Retain the test documentation that the stub does not calculate damage, speed, status, abilities, items, or Random Battle outcomes.

- [ ] **Step 5: Run complete verification.**

~~~powershell
.\\.venv\\Scripts\\python.exe -m pytest -q
~~~

Expected: all tests pass. The expected baseline is the existing 48 tests plus new contract, belief/consequence, gateway, replay, and fixture coverage, with only the existing dependency deprecation warnings unless a new warning is directly caused by the redesign.

- [ ] **Step 6: Commit the verification suite.**

~~~powershell
git add tests/fixtures/mechanics_cases.json tests/unit/test_mechanics_fixtures.py tests/integration/test_e2e_battle.py
git commit -m "test: verify Jev harness mechanics and decision contracts"
~~~

## Foul Play Evaluation Handoff (After Implementation)

This is an evaluation procedure, not a live-harness dependency and not a second paid shadow battle.

1. Run the no-provider full test suite and local RandomPlayer/SimpleHeuristicsPlayer gates.
2. Run a small Jev audit over saved decision packages containing attack-versus-switch, setup, hidden-opponent, double-switch, and endgame positions.
3. Run Foul Play as an external opponent using the official local Showdown engine as referee. Do not modify or import Foul Play source into src/jev_showdown.
4. Record the Foul Play commit, Showdown version, format, search time, parallelism, thread count, match count, outcomes, fallbacks, illegal/stale decisions, and latency.
5. Increase Foul Play search budget only between controlled series; do not interpret one local series as an Elo guarantee.
6. Do not run PokeChamp as a benchmark because it would require additional paid LLM usage.

The first evaluation series must be small. Expand only after there are no illegal orders, stale submissions, protocol failures, or unacceptable latency regressions. This is test execution discipline, not a new cost-control subsystem in the product.

## Plan Self-Review

### Spec coverage

- Truth-first canonical state: Tasks 1, 5, and 7.
- rqid, force-switch, wait, trapped, version, and deadline metadata: Tasks 1, 5, and 7.
- Legal move, Tera, switch, and default actions: Task 2.
- Provenance, units, exact/uncertain consequences, and mechanics oracle boundary: Tasks 3 and 9.
- Hidden active/bench/fainted/unknown opponent slots: Task 4.
- Opponent move/status/setup/switch/unknown responses and double switches: Task 4.
- Neutral strategic hypotheses, history, resources, glossary, and risk framing: Task 5.
- One typed Jev Choice request, strict response validation, and no live debate: Task 6.
- Freshness, legality, fallback, and stale-response rejection: Task 7.
- Replayable decisions, ablations/metrics, and no-provider evaluation: Task 8.
- Foul Play benchmark boundary and no PokeChamp evaluation: the handoff section.
- Latency measurement and live-path boundedness: Tasks 6–8.
- Avoiding action pruning and hard-coded playbook logic: Global Constraints and Tasks 2–4, 7.

### Placeholder scan

This plan contains no implementation placeholders, no unspecified file locations, and no steps that defer a required behavior to a later unnamed task. The interface listing uses pass only as compact signature notation; each task specifies the concrete behavior and test cases that implement those signatures.

### Type consistency

The shared names are stable across tasks: Fact, BattleRequestMetadata, DecisionFingerprint, CandidateAction, JevDecisionResponse, ValidatedOrder, build_candidate_actions, annotate_candidates_with_facts, build_snapshot, extract_request_metadata, build_decision_fingerprint, resolve_order, write_decision_package, read_decision_packages, and summarize_series.

### Review-focus coverage

All five review-focus cases have explicit tests: forced/wait requests in Task 2, fog-of-war in Task 4, Tera and duplicate order mapping in Task 2, stale/malformed responses in Tasks 6–7, and incomplete mechanics in Tasks 3 and 9.
