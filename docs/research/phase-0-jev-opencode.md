# Phase 0 Research Log: Jev through OpenCode

Date checked: 2026-09-19

## Finding

We can use Jev through OpenCode's free hosted route.

Use the OpenCode Zen System One endpoint:

```text
POST https://opencode.ai/zen/v1/systemone
Authorization: Bearer public
Content-Type: application/json
```

Use this model identifier:

```text
jev-1.13-free
```

No TypeSafe API key was required during the live probe.

## Request contract

Jev is not a normal chat-completions model. Send structured state and typed questions:

```json
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
        "earthquake": "Use Earthquake.",
        "switch_rotom": "Switch to Rotom-Wash."
      }
    }
  }
}
```

The response is typed and includes the selected answer, confidence, probabilities, usage, and cost:

```json
{
  "model": "jev-1.13-free",
  "answers": {
    "action": {
      "type": "choice",
      "choice": "earthquake",
      "confidence": 1,
      "probabilities": {
        "earthquake": 1,
        "switch_rotom": 0
      }
    }
  },
  "usage": {
    "input_tokens": 309,
    "output_tokens": 24
  },
  "cost": "0"
}
```

The exact live probe returned `cost: "0"`. This confirms the currently available free route, not an unlimited-quota guarantee.

## What does not work

The normal OpenCode agent path was tested with:

```text
opencode run --model opencode/jev-1.13-free
```

That path produced a provider-side HTTP 500 and an OpenCode `provider.internal` error. The reason is that Jev returns decisions rather than free-form text; the normal chat/agent loop is the wrong protocol.

The Jev adapter must call `/systemone` directly using an asynchronous HTTP client.

## Design implications

- Create a small `JevProvider` interface around the System One request/response contract.
- Keep deterministic battle math and legal-action validation outside Jev.
- Send only legal candidate action IDs in `questions[*].criteria`.
- Batch multiple independent tactical questions into one request where useful.
- Treat confidence and probabilities as first-class telemetry.
- Enforce a short timeout and fall back to a deterministic legal action if the free endpoint is unavailable.
- Log model ID, latency, token usage, reported cost, retries, and fallback decisions.

## Sources

- [OpenCode server documentation](https://opencode.ai/docs/server/)
- [OpenCode provider documentation](https://opencode.ai/docs/providers/)
- [TypeSafe/Jev API guide](https://jevtypesafeai.com/how-to-use)
- [TypeSafe announcement of System One and Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
