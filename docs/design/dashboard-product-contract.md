# Dashboard product contract

Status: authoritative. This document defines product truth and observable
behavior only. It intentionally does not define a visual style, palette,
typography, component geometry, screen composition, or copy system.

## Purpose

The dashboard is a public-facing view of one real autonomous Pokémon battle.
It must let a technical or non-technical viewer understand, from live evidence,
that:

1. Pokémon Showdown provides the battle and protocol state.
2. The application extracts public state and calculates deterministic facts.
3. The application sends a bounded, structured decision request to Jev.
4. Jev returns an actual typed decision.
5. The adapter validates and submits a legal Showdown order.
6. The dashboard reports the result observed from Showdown.

The dashboard is an observer of this chain, not a second battle client and not
a replacement for the battle simulator.

## Source-of-truth boundary

The product must distinguish the origin of every displayed fact:

| Origin | Allowed content |
| --- | --- |
| Showdown | Official battle presentation, public protocol state, submitted order acknowledgement, and observed battle result |
| Harness | Extracted public state, legal candidate actions, deterministic calculations, validation outcome, timing, and request metadata |
| Jev | Fields actually returned by Jev, including a typed choice and any returned confidence or probabilities |
| Adapter | The selected legal order, fallback selection, and submission status |

Use direct, attributable labels when a viewer could otherwise confuse these
origins. Never present a harness calculation as if it came from Jev, or a Jev
field as if it were a Showdown fact.

## Battle ownership

- The official Showdown renderer owns the battle surface and game-state UI.
- Do not redraw or duplicate Pokémon, HP, teams, weather, terrain, effects,
  battle messages, battle logs, or outcome UI elsewhere in the dashboard.
- Integrate the official renderer with the real protocol stream; do not embed a
  complete Showdown website or use a fake battle surface.
- Show only information the current protocol/application state makes
  available. Unrevealed opponent information remains unknown.
- The first product supports one active battle at a time.

## Data integrity

- Render real values from the running application. Do not use fabricated demo
  telemetry in the live path.
- Omit unavailable values or mark them explicitly as unavailable; do not fill
  gaps with guesses.
- Mark deterministic calculations as calculations or estimates and preserve
  relevant assumptions, such as unknown items, abilities, EVs, IVs, or exact
  stats.
- Legal actions must come from the adapter's current legal-order interface.
- The request sent to Jev may include the current public state, field facts,
  legal actions, deterministic annotations, uncertainty markers, and the actual
  question/criteria used by the adapter.
- Secrets, authorization tokens, and unredacted credentials never appear in
  the UI or inspector.

## Jev decision boundary

The dashboard may show the actual Jev decision information returned by the
provider, such as:

- typed action;
- confidence, only when returned;
- probability distribution, only when returned;
- model/provider identifier, only when returned;
- latency, usage, or cost, only when reported by the application/provider;
- provider error, timeout, retry, or fallback status.

The dashboard must not manufacture:

- chain-of-thought or hidden reasoning;
- a prose explanation that Jev did not return;
- win probability, risk score, psychology, damage result, or other model
  output that is not an actual field;
- confidence, probabilities, cost, or usage from an unrelated estimate.

The UI can show the request and response as structured data for inspection. It
must not imply that showing the request is showing Jev's private reasoning.

## Turn lifecycle

The visible lifecycle must follow the real event order. A useful vocabulary is:

`EXTRACTING` → `CALCULATING` → `JEV_EVALUATING` → `LEGAL` →
`ORDER_SUBMITTED` → `AWAITING_SHOWDOWN` → `RESULT_OBSERVED`

Implementations may choose different presentation for these states, but they
must preserve these facts:

- extracting and calculating happen before the request is sent;
- the Jev waiting state represents the provider request, not invented work;
- an action is not shown as legal until current validation succeeds;
- an order is not shown as submitted until the adapter submits it;
- a result is not shown as observed until Showdown produces the corresponding
  protocol/state update;
- timeouts, retries, invalid responses, and fallback orders are explicit and
  attributable;
- a battle outcome is never declared from a local prediction alone.

At startup, connection, matchmaking, active battle, completed battle, and
failure states must be distinguishable. A degraded/fallback state must remain
truthful and visible until the underlying state changes.

## Decision record

For each turn, the application should retain enough structured information to
answer:

- What public state was extracted?
- What deterministic facts and legal candidates were calculated?
- What request/question/criteria was sent to Jev?
- What did Jev actually return?
- Which candidate did the adapter select?
- Did validation pass or fail, and why?
- What exact Showdown order was submitted?
- What timing, usage, cost, retry, or fallback data was reported?
- What result was subsequently observed?

Decision history is history of Jev decisions and adapter actions, not a second
battle log. It resets for a new battle and remains inspectable after a battle
ends until the next battle begins.

## Inspection

Technical viewers need a deliberate inspection path for the current or a
selected decision. It should expose, with secrets redacted, the structured
state snapshot, calculated candidates, request, Jev response, validation,
submitted order, relevant raw protocol frames, and observed result.

Inspection is supplementary evidence. It must not replace the primary view of
the live battle or force viewers to read raw JSON to understand the basic
event sequence.

## Interaction limits

- Provide a clear way to start the autonomous battle and a truthful status
  while it runs.
- Do not provide manual move selection, manual order submission, or controls
  that imply the viewer is playing the agent's battle.
- Avoid settings, replay, recording, or multi-battle orchestration unless a
  later product decision explicitly adds them.
- Use wording that names real data, events, or actions. Do not add slogans,
  marketing claims, or labels whose only purpose is to make the interface look
  informative.

## Usability and accessibility

- The main experience must be understandable on a normal desktop or laptop
  landscape viewport without excessive scrolling.
- Critical live state, Jev's actual decision, and the current adapter status
  must remain readable at the same time or through an obvious, low-friction
  interaction.
- Use semantic controls and status announcements appropriate to their meaning.
- Color must not be the only way to communicate legality, failure, fallback,
  or result state.
- Loading and error states must be visible without blocking the whole page in a
  large modal.

These are usability outcomes, not a prescription for columns, panels, cards,
rails, timelines, drawers, or any other visual component.

## Verification bar

Before calling a dashboard implementation ready:

- exercise the real Showdown/agent route, not only a mocked browser state;
- verify that displayed decision data is derived from the live event stream;
- verify fallback, timeout, invalid-response, and battle-complete states;
- verify that no duplicate battle UI or fabricated Jev reasoning appears;
- verify a normal landscape viewport with Playwright and inspect screenshots as
  a human viewer would;
- verify there is no accidental overflow, overlap, unreadable text, or
  interaction that requires excessive scrolling;
- run the relevant automated tests and record any known environmental limits.

## Creative authority

Future implementation agents are expected to invent the visual solution. They
may choose the visual language, colors, typography, composition, density,
animation, information hierarchy, and component vocabulary as long as the
behavioral contract above is met.

No other dashboard design document is authoritative. Historical plans,
mockups, screenshots, and validation records must not be treated as visual
requirements.
