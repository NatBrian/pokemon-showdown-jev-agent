# Jev AI by TypeSafe AI: Research Notes

Research date: 2026-09-20  
Scope: Jev and the TypeSafe System One model contract only.

This note was written from the official TypeSafe AI documentation, TypeSafe AI's launch material, and the official OpenCode Zen documentation. Existing Markdown files under `docs/research` were intentionally not opened or used.

## Executive summary

Jev is TypeSafe AI's first public **System One model**. It is designed for software-to-AI interaction, not for conversation with a human.

The simplest mental model is:

```text
state + typed questions
        ↓
Jev evaluates the questions
        ↓
typed answers + probabilities + confidence
```

Jev is not primarily a text generator. It does not return a paragraph explaining what it thinks. The application defines the answer space in advance, and Jev returns a value inside that space. The surrounding program then decides what to do with the answer.

TypeSafe describes Jev as a machine-native intelligence primitive: fast, structured, composable, observable, and intended to be placed inside ordinary software. The official introduction describes System One models as models that make fast structured decisions software can use directly, with Jev as the first public model.

Sources:

- [TypeSafe AI: System One and Jev](https://docs.typesafe.ai/concepts/system-one)
- [TypeSafe AI: Introduction](https://docs.typesafe.ai/introduction)
- [TypeSafe AI: Introducing System One Models & Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)

## 1. What Jev is

Jev is a decision model rather than a chat model.

TypeSafe's stated design target is machine-to-machine and machine-to-software automation. The model still understands natural-language input, but the output contract is different from an LLM chat response:

| Conventional chat LLM | Jev / System One |
| --- | --- |
| Produces generated text | Produces typed values |
| The application parses the text | The application reads structured answer fields |
| The model can invent arbitrary wording | The application defines the allowed answer space |
| Confidence is usually requested in the prompt | Probability distributions and confidence are part of the answer contract |
| Often used as a conversational agent | Intended to be a decision primitive inside a workflow |

TypeSafe says Jev uses a new model architecture, a parallel sampler, and a training method called **Reinforcement Learning for Calibrated Decisions (RLCD)**. The public material explains the intended behavior and API, but does not provide enough implementation detail to independently reconstruct the architecture or training system.

Jev should therefore be understood by its observable contract, not by assuming that it is merely a small language model with JSON mode.

## 2. What Jev receives

Every request contains three top-level fields:

```json
{
  "model": "jev-latest",
  "state": {},
  "questions": {}
}
```

### `state`

`state` is the material Jev evaluates. It can be:

- a string;
- a structured JSON object; or
- an array containing related text/context.

TypeSafe recommends using an object for most applications because named fields make relationships and context easier to understand. The state should contain the evidence, records, policies, or current application state needed for the judgment.

Jev currently accepts text and structured textual state only. Images, audio, and video are not supported in the documented model contract.

The application must include any context Jev needs in the request. The public API contract describes each request as one state evaluated against one or more questions; it does not describe a conversational memory or hidden application memory. The safe integration assumption is that Jev is stateless between calls unless the application puts history into `state`.

Source: [TypeSafe AI: State](https://docs.typesafe.ai/concepts/state).

### `questions`

`questions` is a map from application-defined question IDs to typed question definitions.

Each question has:

- an ID chosen by the application;
- a `type`;
- `instructions`; and
- sometimes `criteria`.

The ID is used to match the response to the original question. TypeSafe's documentation says question IDs are for the application and are not sent to the underlying model, so the instructions must still state the complete judgment being requested.

The `instructions` may be a string, object, or array. Structured instructions can keep a question, supporting data, and references together. The documentation recommends referring to named state fields explicitly when a question depends on a particular part of structured state.

## 3. The three Jev question types

### Choice

Use `choice` when the answer must be one option from a known set without an inherent ordering.

```json
{
  "route": {
    "type": "choice",
    "instructions": "Which team should handle this request?",
    "criteria": {
      "billing": "Payments, invoices, and refunds",
      "technical": "Bugs, outages, and integrations",
      "sales": "Pricing and new accounts"
    }
  }
}
```

The response contains:

- `choice`: the selected option key;
- `probabilities`: a probability for every supplied option; and
- `confidence`: a summary of the distribution's concentration.

The API supports up to 255 options for one Choice question. If the possible options are not exhaustive, the documentation recommends adding an `other` or `none_of_the_above` option.

### Score

Use `score` when the answer belongs on an ordered rubric or spectrum.

```json
{
  "severity": {
    "type": "score",
    "instructions": "How severe is the issue?",
    "criteria": [
      "Routine",
      "Important",
      "Urgent",
      "Critical"
    ]
  }
}
```

The response contains:

- `score`: a probability-weighted value, which may fall between levels;
- `legend`: the numbered levels and their descriptions;
- `probabilities`: the distribution across levels; and
- `confidence`.

A Score is not the same as several unrelated classifications. The levels must have a meaningful order.

### Noul

Use `noul` for a clearly defined yes/no judgment where the probability of “yes” is useful.

```json
{
  "needs_review": {
    "type": "noul",
    "instructions": "Does this case require human review?"
  }
}
```

The response contains `noul`, a number from 0 to 1:

- near `1`: strong yes;
- near `0`: strong no;
- near `0.5`: uncertain.

Noul does not have a separate `confidence` field because its value is already the yes probability.

Sources:

- [TypeSafe AI: Primitives](https://docs.typesafe.ai/primitives)
- [TypeSafe AI: API Reference](https://docs.typesafe.ai/api)

## 4. Jev's response contract

A normal response contains the resolved model name, one answer for every question, and token usage:

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "route": {
      "type": "choice",
      "choice": "technical",
      "probabilities": {
        "billing": 0.15,
        "technical": 0.85,
        "sales": 0.0
      },
      "confidence": 0.78
    }
  },
  "usage": {
    "input_tokens": 392,
    "output_tokens": 65
  }
}
```

For Choice answers, TypeSafe documents that:

- the returned `choice` is the highest-probability option;
- the probability map covers the options supplied in `criteria`; and
- the probabilities sum to 1.

For Score answers, the score can be fractional because it is probability-weighted across the ordered levels.

The TypeSafe API documents standard error responses:

- `401`: missing or invalid API key;
- `422`: invalid request shape or question;
- `429`: rate limit exceeded;
- `529`: service temporarily overloaded.

For `429` and `529`, TypeSafe recommends exponential backoff and honoring `Retry-After` when present. The official SDKs handle retry behavior by default; direct HTTP integrations must implement their own policy.

Source: [TypeSafe AI: API Reference](https://docs.typesafe.ai/api).

## 5. Probability and confidence: the most important distinction

Jev returns both probabilities and confidence, but they are not interchangeable.

### Probabilities

For a Choice question, the probability distribution expresses how probability is distributed across the available options. It is the detailed output that can be logged, thresholded, calibrated, or combined by application code.

For example:

```text
option_a: 0.55
option_b: 0.35
option_c: 0.10
```

This says that option A is preferred, but the decision is not overwhelmingly clear.

### Confidence

TypeSafe says `confidence` is a statistic derived from the probability distribution. It summarizes how concentrated or flat the distribution is. A concentrated distribution generally produces higher confidence; a spread-out distribution produces lower confidence.

Confidence is therefore not automatically the same thing as the winning option's probability. The full probability distribution is available when the application needs a more specific measure.

### Calibration

TypeSafe defines calibration across groups of predictions:

- predictions assigned probability `0.2` should be correct about 20% of the time;
- predictions assigned probability `0.8` should be correct about 80% of the time;
- predictions assigned probability `1.0` should be correct about 100% of the time.

This is a population-level property, not a guarantee for one individual answer. A confidence of `0.9` does not make one decision certain. It means that the model's uncertainty signal is intended to be useful when evaluated over many comparable decisions.

Source: [TypeSafe AI: Confidence](https://docs.typesafe.ai/confidence) and [TypeSafe AI: AI Primer](https://docs.typesafe.ai/introduction/machine-learning-primer).

## 6. How TypeSafe expects Jev to be used

The core design rule is: **one focused judgment per question**.

TypeSafe explicitly warns against asking one broad question such as:

```text
Analyze everything and determine the best course of action.
```

That kind of request requires extended reasoning and mixes multiple dimensions. The recommended approach is to ask smaller questions and combine their answers in normal code.

For example, a workflow can ask separately about:

- risk;
- urgency;
- expected value;
- confidence in the available evidence; and
- policy compliance.

The application can then apply deterministic weights, thresholds, or safety rules.

### Independent questions in one call

Multiple questions in one request:

- see the same state;
- are evaluated independently;
- can mix Choice, Score, and Noul; and
- return separate typed answers.

TypeSafe says adding questions should add little response latency because Jev evaluates them in parallel. Questions do not become hidden context for one another. If question B truly depends on the answer to question A, the application must make a second request after receiving A, or provide both questions together and combine them in code when no real dependency exists.

### Speculative fan-out

The recommended pattern is to ask several potentially useful questions in one request, even if some answers will only matter for certain states. The code can ignore irrelevant answers after the response arrives.

This is useful because one state can support many small judgments without requiring a separate model call for every dimension.

### Confidence-gated behavior

TypeSafe recommends using confidence as a control signal:

```text
high confidence   → act automatically
medium confidence → act cautiously, verify, or request confirmation
low confidence    → do not guess; escalate or use another path
```

The thresholds are application-specific. Low-risk actions can use a lower threshold; irreversible or high-risk actions should require more confidence and possibly an independent deterministic check.

### Application composition

Jev is not intended to own the complete workflow. The application should:

1. prepare the relevant state;
2. define narrow typed questions;
3. receive the answers and probability distributions;
4. combine them with deterministic logic;
5. apply safety and legality checks; and
6. choose whether to act, retry, escalate, or abstain.

This surrounding code is part of the system's reliability. Jev constrains the AI answer space, but the application still owns business rules, authorization, validation, and execution.

Sources:

- [TypeSafe AI: Primitives](https://docs.typesafe.ai/primitives)
- [TypeSafe AI: Patterns](https://docs.typesafe.ai/patterns)
- [TypeSafe AI: Confidence](https://docs.typesafe.ai/confidence)

## 7. What “type-safe” means, and what it does not mean

In the public contract, type safety means that Jev returns the answer shape and value space defined by the question.

For a Choice question with options `a`, `b`, and `c`, the answer is constrained to those options and the probability map covers those options. The model does not need to invent a prose answer that the application must parse.

That eliminates a major class of errors:

- malformed natural-language output;
- extra explanation mixed into an action;
- unknown option names;
- invalid JSON-style values generated by a text model; and
- regex or parser ambiguity.

It does **not** mean:

- the selected option is semantically correct;
- the state is complete or accurate;
- the question is well-designed;
- a probability is a guarantee for one case;
- the model understands hidden information; or
- the application can skip validation and safety rules.

“No hallucinations” should therefore be interpreted as no free-form answer outside the declared output schema, not as a guarantee that Jev can never make a wrong judgment.

## 8. Versioning, models, and deployment channels

The official TypeSafe endpoint is:

```text
POST https://api.typesafe.ai/v1/systemone
```

The official documentation currently lists:

- `jev-1.13.0`: the versioned Jev 1.13 model;
- `jev-latest`: an alias for the most recent stable release; and
- `jev-preview`: an alias for the newest release, including preview builds when available.

Aliases can move when a new model release ships. TypeSafe recommends pinning a version when confidence thresholds or production behavior depend on a particular model version. The response's `model` field reports the version that actually answered.

OpenCode Zen exposes Jev through a compatible System One endpoint:

```text
POST https://opencode.ai/zen/v1/systemone
```

The current OpenCode model listing includes:

- `jev-1.13`;
- `jev-1.13-free`.

The public documentation confirms the IDs and endpoint, but it does not document the exact quality, training, latency, or quota differences between the paid and free Jev offerings. They should be treated as separate deployment profiles and measured separately rather than assumed to be identical.

Sources:

- [TypeSafe AI: Models](https://docs.typesafe.ai/models)
- [OpenCode Zen: Jev](https://opencode.ai/docs/en/zen/)
- [OpenCode Zen model listing](https://opencode.ai/zen/v1/models)

## 9. Limits and cost information

The official TypeSafe model documentation currently states:

- context: up to 64k tokens for state plus all questions;
- additional limit: 32k tokens for state plus the longest individual question;
- rate limit: 250,000 tokens per second and 1,200 requests per minute;
- input: text and structured textual state only;
- paid Jev 1.13 price: $0.042 per million input tokens;
- output tokens: free according to the published price table.

The same documentation warns that rate limits are being adjusted dynamically and may change. The free offering is listed as free, but availability and service conditions can change.

For a fast decision loop, the important practical limit is not only tokens. It is also the application's end-to-end latency budget, the service's rate limits, retry behavior, and the time available for the surrounding system to validate and execute the answer.

Source: [TypeSafe AI: Models](https://docs.typesafe.ai/models).

## 10. What is still unknown

The public official material does not currently answer several questions in enough technical detail to treat them as facts:

### Is Jev deterministic?

The public documentation lists this as a question but does not provide a definitive answer. We should not assume identical responses for identical requests. If reproducibility matters, test repeated identical calls and record the model version, state, questions, probabilities, and response time.

### Does Jev have hidden memory or conversation state?

The API is documented as evaluating one supplied state against one or more questions. No hidden application memory is documented. The safe assumption is stateless requests: include the context needed for every judgment.

### Is Jev a smaller LLM?

TypeSafe explicitly positions System One as a new model class and says it uses a new architecture, sampler, and training approach. Public documentation does not provide enough technical detail to classify its internal architecture. We should use the observable API contract rather than speculate.

### Does confidence predict correctness for this particular task?

TypeSafe's goal is calibrated confidence, but calibration must be checked on the application's own task distribution. The vendor's definition is statistical across groups of predictions. A confidence threshold should be validated against recorded outcomes, not accepted blindly.

### What exactly is different about `jev-1.13-free`?

OpenCode exposes both paid and free IDs, but the public sources reviewed here do not specify whether the difference is quota, access, infrastructure, model weights, quality, or another service policy. Do not assume paid and free results are interchangeable.

### Does Jev explain its reasoning?

No. System One documentation says these models return decisions and probabilities rather than generated explanations of their reasoning. The application may expose the state, question, probabilities, confidence, and deterministic post-processing, but should not invent a reasoning trace that Jev did not return.

## 11. Practical mental model for future integration work

The right abstraction is not:

```text
Send Jev a prompt and parse its answer.
```

It is:

```text
Define an information state
    ↓
Define a finite answer space or rubric
    ↓
Ask one focused question per judgment
    ↓
Receive constrained answers and distributions
    ↓
Use confidence to decide whether to trust, verify, or abstain
    ↓
Compose the final action in deterministic application code
```

The model is strongest when the application performs the exact work that software is good at:

- collecting and normalizing facts;
- enforcing legal options;
- supplying complete context;
- defining clear labels and boundaries;
- combining independent judgments; and
- validating the final action.

Jev contributes the judgment where fixed rules are too brittle, while the application remains responsible for correctness, execution, and safety.

## Sources consulted

Official TypeSafe AI:

- [Introduction](https://docs.typesafe.ai/introduction)
- [Quick start](https://docs.typesafe.ai/introduction/quickstart)
- [System One](https://docs.typesafe.ai/concepts/system-one)
- [State](https://docs.typesafe.ai/concepts/state)
- [Primitives](https://docs.typesafe.ai/primitives)
- [Confidence](https://docs.typesafe.ai/confidence)
- [AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer)
- [API reference](https://docs.typesafe.ai/api)
- [Models](https://docs.typesafe.ai/models)
- [Introducing System One Models & Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)

Official OpenCode:

- [OpenCode Zen documentation: Jev](https://opencode.ai/docs/en/zen/)
- [OpenCode Zen model listing](https://opencode.ai/zen/v1/models)

