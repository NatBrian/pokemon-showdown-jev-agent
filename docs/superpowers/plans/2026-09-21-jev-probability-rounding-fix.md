# Jev Probability Rounding Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent Jev's harmless rounded probability vectors from causing unnecessary deterministic fallbacks while continuing to reject materially malformed provider responses.

**Architecture:** Keep action identity, legal-action validation, and confidence validation unchanged. At the typed Jev protocol boundary, accept a probability total within a fixed `0.01` absolute tolerance because the observed Jev response rounded nine probabilities to two decimals and produced `0.99`; normalize accepted probabilities to a unit sum before returning them. A materially invalid total remains an error and continues through the existing legal fallback path.

**Tech Stack:** Python 3.11, `pytest`, `httpx`, existing Jev protocol/client and `JevPlayer` fallback path.

**Spec:** `docs/superpowers/plans/2026-09-21-jev-harness-redesign.md`; the live failure evidence is `artifacts/foul-play-evaluation-final-10s-2026-09-21/final-audit.json` and call 2 in `jev-request-response.jsonl`.

## Global Constraints

- Do not make Jev API calls during implementation or provider-free verification.
- Do not change Pokémon strategy, candidate generation, legal-action pruning, or fallback ordering.
- Accept only the observed small rounding discrepancy (`abs(sum - 1.0) <= 0.01`); materially malformed distributions remain rejected.
- Preserve the provider's original response in `raw_response`; only the typed `probabilities` result is normalized.
- Run the full provider-free suite before considering another paid Foul Play evaluation.
- Never automatically repeat a paid battle series after a protocol or validation failure.

## Review Focus

- A rounded vector such as the saved `0.99` response must be accepted and normalized without changing the selected choice.
- A materially wrong vector such as a total of `0.80` must still be rejected and produce the existing legal fallback behavior.
- Missing or extra action IDs must remain rejected even when the numeric total is near one.
- Empty or all-zero probability maps must not be normalized into a false distribution.
- Exact unit-sum vectors must preserve their values closely enough for existing telemetry and tests.

### Task 1: Make the Jev protocol tolerant to provider rounding

**Files:**
- Modify: `src/jev_showdown/decision/protocol.py`, inside `validate_jev_choice`
- Test: `tests/unit/test_jev_client.py`

**Interfaces:**
- Consumes: the existing Jev response mapping and criteria mapping passed to `validate_jev_choice`.
- Produces: the same `(choice, confidence, probabilities)` tuple; accepted near-unit probability maps are returned normalized to sum to one.

- [x] **Step 1: Add the failing regression test for the saved response shape**

Add this test to `tests/unit/test_jev_client.py`:

```python
@pytest.mark.asyncio
async def test_jev_client_accepts_observed_rounded_probability_distribution(test_settings):
    mock_payload = {
        "model": "jev-1.13-free",
        "answers": {
            "action": {
                "type": "choice",
                "choice": "move_sludgebomb",
                "confidence": 0.79,
                "probabilities": {
                    "move_earthquake": 0,
                    "move_recover": 0,
                    "move_sludgebomb": 0.81,
                    "move_stealthrock": 0.03,
                    "switch_cloyster": 0.04,
                    "switch_darkrai": 0.05,
                    "switch_magmortar": 0.02,
                    "switch_mienshao": 0.04,
                    "switch_volbeat": 0,
                },
            }
        },
        "usage": {"input_tokens": 1, "output_tokens": 1},
        "cost": "0",
    }
    client = JevSystemOneClient(test_settings)
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(
            200,
            json=mock_payload,
            request=httpx.Request("POST", test_settings.jev_endpoint),
        )

        result = await client.evaluate_decision(
            state={"turn": 2},
            criteria={key: f"Use {key}" for key in mock_payload["answers"]["action"]["probabilities"]},
        )

    assert result.error is None
    assert result.choice == "move_sludgebomb"
    assert sum(result.probabilities.values()) == pytest.approx(1.0)
    assert result.probabilities["move_sludgebomb"] == pytest.approx(0.81 / 0.99)
    assert result.raw_response == mock_payload
```

- [x] **Step 2: Run the new test and verify the expected failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_jev_client.py::test_jev_client_accepts_observed_rounded_probability_distribution -q
```

Expected: FAIL with `Invalid Jev Choice response: probability sum must equal 1.0`.

- [x] **Step 3: Implement the smallest protocol fix**

In `validate_jev_choice`, keep the existing key, numeric, finite, and range checks. Replace only the exact-sum rejection with a fixed rounding tolerance and normalization:

```python
PROBABILITY_SUM_TOLERANCE = 0.01

total = sum(probabilities.values())
if abs(total - 1.0) > PROBABILITY_SUM_TOLERANCE:
    raise JevChoiceValidationError("probability sum must equal 1.0")
if total <= 0.0:
    raise JevChoiceValidationError("probability sum must be positive")
probabilities = {key: value / total for key, value in probabilities.items()}
```

Keep the constant near the protocol validator, add a short comment explaining that it covers Jev's observed two-decimal rounding, and do not widen it based on later failures without a new evidence-backed test.

- [x] **Step 4: Run the regression test and verify it passes**

Run the same test command from Step 2.

Expected: PASS; the response is accepted, the choice remains `move_sludgebomb`, and the typed probabilities sum to one.

- [x] **Step 5: Add the material-invalid and structural-invalid tests**

Add these tests to the same file:

```python
@pytest.mark.asyncio
async def test_jev_client_rejects_materially_invalid_probability_distribution(test_settings):
    payload = {
        "model": "jev-1.13-free",
        "answers": {"action": {
            "type": "choice",
            "choice": "move_earthquake",
            "confidence": 0.8,
            "probabilities": {
                "move_earthquake": 0.7,
                "switch_rotom": 0.1,
            },
        }},
    }
    client = JevSystemOneClient(test_settings)
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(
            200, json=payload, request=httpx.Request("POST", test_settings.jev_endpoint)
        )
        result = await client.evaluate_decision(
            state={"turn": 2},
            criteria={"move_earthquake": "Use Earthquake", "switch_rotom": "Switch Rotom"},
        )

    assert result.choice is None
    assert "probability sum" in (result.error or "")


@pytest.mark.asyncio
async def test_jev_client_still_rejects_missing_probability_ids_near_unit_sum(test_settings):
    payload = {
        "model": "jev-1.13-free",
        "answers": {"action": {
            "type": "choice",
            "choice": "move_earthquake",
            "confidence": 0.8,
            "probabilities": {"move_earthquake": 1.0},
        }},
    }
    client = JevSystemOneClient(test_settings)
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(
            200, json=payload, request=httpx.Request("POST", test_settings.jev_endpoint)
        )
        result = await client.evaluate_decision(
            state={"turn": 2},
            criteria={"move_earthquake": "Use Earthquake", "switch_rotom": "Switch Rotom"},
        )

    assert result.choice is None
    assert "missing criteria IDs" in (result.error or "")
```

- [x] **Step 6: Run the focused client and fallback tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_jev_client.py tests/unit/test_agent.py tests/unit/test_validator_and_fallback.py -q
```

Expected: all tests pass; no network request is made because `httpx.AsyncClient.post` is mocked.

- [x] **Step 7: Run the complete provider-free suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass, with only the two existing dependency deprecation warnings.

### Task 2: Replay the paid failure without Jev and decide the evaluation gate

**Files:**
- Create: `artifacts/foul-play-evaluation-final-10s-2026-09-21/protocol-replay.json`
- Modify: `docs/superpowers/plans/2026-09-21-foul-play-max-strength-three-battle-evaluation.md`
- Modify: `.superpowers/sdd/foul-play-max-strength-three-battle-evaluation/progress.md`

**Interfaces:**
- Consumes: the saved call-2 raw response in `jev-request-response.jsonl` and the corrected `validate_jev_choice` implementation.
- Produces: a provider-free replay record showing the saved response is now accepted and normalized, plus a documented paid-test gate.

- [x] **Step 1: Run a provider-free replay against the saved raw response**

Use a short Python command that loads call 2 from `jev-request-response.jsonl`, passes its `answers` object and the saved request criteria into `validate_jev_choice`, and writes only the result summary to `protocol-replay.json`. The summary must contain `source_call_id: 2`, `choice: move_sludgebomb`, `accepted: true`, `raw_probability_sum: 0.99`, `normalized_probability_sum: 1.0`, and `jev_api_calls: 0`; it must not copy credentials or the full provider response.

Expected: the command exits 0 and writes the summary with the exact fields above.

- [x] **Step 2: Run the replay assertions**

Run:

```powershell
.\.venv\Scripts\python.exe -c "import json; from pathlib import Path; d=json.loads(Path('artifacts/foul-play-evaluation-final-10s-2026-09-21/protocol-replay.json').read_text()); assert d['accepted'] is True; assert d['jev_api_calls']==0; assert abs(d['normalized_probability_sum']-1.0)<1e-9; print(d)"
```

Expected: PASS and `jev_api_calls=0`.

- [x] **Step 3: Record the gate decision**

Document that the provider-free fix is verified, the previous stop was a protocol-rounding false positive rather than a strategic failure, and one fresh fixed three-battle Foul Play series may be run only after all tests pass. The next series must still stop immediately on any material invalid response, recorder error, illegal order, stale response, timer failure, or provider failure; do not spend calls on retries or shadow battles.

- [x] **Step 4: Final verification**

Run:

```powershell
git diff --check
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: no diff errors and the full provider-free suite passes.

## Final Evaluation Result (2026-09-21)

After the provider-free fix gates passed, one fixed three-battle Foul Play series was run at the already calibrated 10000 ms search configuration. The series completed normally with 3 battles, 74 Jev calls, 74 decisions, 0 fallbacks, 0 provider errors, 0 illegal actions, and 0 stale responses. Decision latency was p50 `1171.7814 ms`, p95 `1964.927885 ms`, and p99 `2407.074736 ms`. Four raw Jev probability vectors had small rounding discrepancies and were accepted/normalized.

Jev won 1 battle and lost 2, for a 33.33% three-battle sample win rate. This is a valid strategic result, but it does not establish that the current system can beat Foul Play. No further Jev call, retry, search escalation, shadow battle, dashboard run, or PokeChamp run was started. The authoritative evaluation record is `artifacts/foul-play-evaluation-after-probability-fix-10s-2026-09-21/final-audit.json`.

## Subsequent Offline Harness Isolation Fix (2026-09-21)

An offline audit of the final series found that battle 47's first Jev request included the tail of battle 46 in its `history` field. The cause was a process-wide `TurnHistoryTracker` in `JevPlayer`; scanner instances were battle-tag scoped, but decision history was not, and the finished battle never removed its history.

The remediation is recorded in `docs/superpowers/plans/2026-09-21-per-battle-history-isolation.md`. `JevPlayer` now resolves history by battle tag, retains the existing injected/default tracker for the first battle for compatibility, flushes scanner events before discarding a finished battle's tracker, and does not change candidate generation or Jev response validation. The red regression test reproduced the leak before the fix and passed after it; focused tests passed with `18 passed`, and the full provider-free suite passed with `107 passed, 2 warnings`.

No additional Jev API calls were made. The existing paid `1-2` result was produced before this history-isolation remediation, so it is evidence about the then-current implementation but is not a clean post-fix measurement. A future clean paid retest would be needed to measure whether this correction improves results; it is not being run automatically.
