# Project Discussion and Alignment Record

Status: Discussion record only. This is not an implementation plan.  
Date recorded: 2026-09-19

This document records what the project owner and assistant discussed and agreed on so future work can recover the intended direction without repeating the conversation or accidentally expanding the project scope.

Do not treat this document as permission to begin implementation planning. The project owner explicitly said that planning should wait until the discussion is finished.

## 1. Core project purpose

The project is an autonomous Pokémon Showdown agent for Generation 9 Random Battles powered by Jev AI.

The main purpose is not to write an essay about Jev. The main purpose is to create a visual, working showcase where viewers can observe Jev making decisions in a real game.

The audience should be able to understand:

- what Jev receives as input;
- what Jev returns as output;
- what actions are available;
- how the selected action is sent to the game;
- what happens after the action;
- why a typed decision model is useful for real-time decision-making.

The project should allow people to clone the GitHub repository and run it themselves locally. There should be no paid hosting requirement and no unnecessary cloud infrastructure.

The project owner will record the showcase video.

## 2. Intended message of the showcase

The audience should infer from the working demonstration that Jev is different from a chat-based LLM and different from a purely deterministic rules engine.

The intended conceptual message is:

- A chat-based LLM produces conversational text that another program must interpret.
- A deterministic bot follows rules and calculations but has limited qualitative judgment.
- Jev receives structured application state and explicit questions, then returns a typed decision suitable for direct action selection.
- Jev is intended to provide intelligence for decision-making while deterministic software handles exact rules and safety.

The project must demonstrate this through visible evidence rather than a long written explanation.

The dashboard and recorded video will not display explicit comparative marketing claims. Viewers should infer the difference from the observable behavior and measured results. Internal documentation may describe the intended comparison so the project direction is not forgotten.

## 3. Audience

The showcase has two audiences equally:

1. General technology and LinkedIn audiences who need a simple visual explanation.
2. AI/ML and software engineers who want to inspect the technical input, output, and decision flow.

The visual experience should therefore have two layers:

- A simple, attractive default view that is immediately understandable.
- Technical information rendered visually for deeper inspection.

Raw JSON may exist for internal debugging or a technical inspection panel, but the primary interface should not be a wall of JSON.

## 4. Jev and model scope

The project focuses only on Jev.

We will not integrate:

- Claude;
- GPT;
- Gemini;
- another chat-based LLM;
- a custom LLM comparison agent;
- a custom competing strategy bot.

The purpose is to showcase Jev itself. Comparisons to LLMs and deterministic software are explanatory concepts and evaluation context, not additional systems that must be implemented in this project.

The Jev route already investigated is the free OpenCode System One endpoint using model identifier "jev-1.13-free". The normal OpenCode chat/agent command is not the battle transport.

The working Jev integration is documented separately in:

- docs/research/phase-0-jev-opencode.md
- docs/research/phase-1-research-and-architecture.md

## 5. Simplicity requirement

The project must be simple and efficient. Avoid overengineering.

The two most important success criteria are:

1. Jev can actually play a complete Gen 9 Random Battle using the correct Showdown architecture, battle logic, and harness.
2. The project has a beautiful visual showcase that makes Jev's behavior understandable and interesting to watch.

Do not add complexity merely because it could be useful in a larger production system.

Out of scope for the initial project direction:

- paid hosting;
- cloud deployment;
- databases;
- complex frontend frameworks unless clearly necessary;
- multi-agent orchestration;
- custom competitor models;
- large benchmark infrastructure;
- unnecessary plugin or service abstractions;
- elaborate analytics that do not help explain Jev.

## 6. Execution and distribution

The intended user journey is local:

~~~
git clone the repository
install the required local dependencies
run the project
open the local browser dashboard
click Start Jev Battle
watch Jev play
~~~

The showcase should not require the viewers to pay for hosting or API calls. The free Jev route through OpenCode is the intended decision service.

Public matchmaking will use a dedicated Showdown account. Credentials will be stored locally in `.env` and must never appear in the dashboard or logs. Account creation has not happened yet; the assistant may attempt it during setup, and the project owner will create the account if signup requires a human step such as CAPTCHA or email verification.

The primary supported environment is the project owner's Windows PC. Cross-platform support is not an MVP requirement.

## 7. Pokémon Showdown format

The game is Pokémon Showdown Generation 9 Random Battles.

The project should use the real Showdown battle environment and the correct Gen 9 Random Battle format, not a simplified imitation of Pokémon combat.

The agent must handle real battle state and legal orders, including relevant mechanics such as:

- active Pokémon;
- living and fainted bench Pokémon;
- moves and disabled moves;
- switching;
- status;
- stat stages;
- hazards;
- weather and terrain;
- Terastallization;
- imperfect information;
- turn timers;
- server requests and action validation.

The game harness is expected to use poke-env for the first implementation because it already exposes Showdown battle state and legal orders.

## 8. Browser dashboard direction

The showcase will use a local browser dashboard.

The dashboard should open in an idle state with a clear button:

~~~
START JEV BATTLE
~~~

The intended behavior is:

1. The user runs the project locally.
2. The browser dashboard opens.
3. The user clicks Start Jev Battle.
4. The agent starts or connects to a Gen 9 Random Battle.
5. Jev makes decisions turn by turn.
6. The dashboard updates live.
7. The battle continues until completion.

The first version should support one active battle at a time. Restarting or starting another battle can be supported without introducing multi-battle orchestration.

The recommended visual approach is a lightweight local browser interface with plain HTML, CSS, and JavaScript served locally by the Python application. The visual should not require React, a large frontend toolchain, or cloud hosting unless later discussion shows a clear need.

## 9. Dashboard visual structure

The visual structure is intentionally undecided. Preserve the product behavior
and transparency requirements in
[dashboard-product-contract.md](design/dashboard-product-contract.md), but do
not treat this discussion record as prescribing a palette, typography,
component arrangement, or screen geometry.

## 10. Transparency requirements

Transparency is a core feature.

For every turn, the dashboard should expose every observable part of the decision process that is available to the application:

- exact state sent to Jev;
- exact questions;
- exact criteria/action definitions;
- all legal candidate actions;
- deterministic calculations used by the harness;
- exact Jev response;
- selected typed action;
- confidence;
- probability distribution;
- latency;
- token usage;
- reported cost;
- exact Showdown order submitted;
- action result;
- timeout, retry, validation, or fallback events.

Nothing observable should be intentionally hidden from a technical viewer.

However, the interface must not fabricate internal model reasoning. If Jev does not return a chain-of-thought or natural-language explanation, the dashboard must not invent one.

The dashboard should present observable decision data and clearly distinguish:

- Jev's actual returned fields;
- deterministic facts calculated by the harness;
- the action selected by the adapter;
- the result produced by Showdown.

Secrets such as authorization tokens must never be displayed.

Logs are for project debugging and do not need a user-facing download feature. Detailed logs can remain local and should be redacted.

## 11. Image/mockup direction

Previous mockups and generated visual references are retired. They are not
implementation requirements. The remaining terminology rule is behavioral:
wording must not imply that Jev exposes hidden chain-of-thought when the
application only has a typed response.

## 12. Opponents and evaluation

There are two different evaluation purposes.

### Public showcase

The primary Start Jev Battle flow should use public Showdown matchmaking for a real Gen 9 Random Battle opponent.

This is intended to show Jev operating in the real game environment.

Public results may be accompanied by:

- replay link;
- format;
- account name;
- game count;
- date;
- Elo;
- GXE;
- Glicko-1;
- latency and fallback information from the local dashboard.

Public matchmaking is not a fixed difficulty ladder. Opponents vary with the active player pool and account rating.

### Controlled local evaluation

For repeatable development checks, Jev should compete against existing players provided by poke-env.

We are not writing these comparison bots.

The proposed progression is:

1. RandomPlayer: easy/connectivity and legality smoke test.
2. MaxBasePowerPlayer: simple tactical reference.
3. SimpleHeuristicsPlayer: first meaningful heuristic baseline.
4. Existing stronger external Gen 9 agent: future improvement.

For a video or game-like presentation, one Jev win can unlock the next opponent tier.

For accurate scientific evaluation, do not rely on one win per tier. Pokémon battles have random teams, critical hits, misses, and matchup variance. Use multiple battles per tier and report win rate, uncertainty, latency, fallback rate, and illegal-action rate.

## 13. Human comparison

A human challenge is not a bot. It is a battle where the opponent is a real human.

Human challenges are optional qualitative evidence and may be useful for a future recording. They are not the current controlled benchmark.

One human match cannot establish human-level strength. To support a claim that Jev is comparable to human Showdown players, the project would need a sustained public ladder run or a future controlled match set, with enough games and rating uncertainty reported.

Public Elo/GXE/Glicko-1 provide a more meaningful human-player comparison than a single win/loss result.

## 14. Showdown leaderboard understanding

Showdown provides a public rated ladder with Elo, GXE, and Glicko-1.

Showdown does not provide a fixed easy-to-hard sequence of opponents. The public ladder is a dynamic matchmaking and rating environment.

The project therefore distinguishes:

- public ladder: real-world performance and human-player comparison;
- local staged ladder: reproducible progression against pinned reference players;
- human challenge: qualitative demonstration;
- replay data: evidence and inspection.

The local staged ladder is an evaluation harness using existing reference players. It is not a new competitive bot ecosystem.

## 15. Important corrections made during discussion

### Correction 1: No competitor models

The project does not integrate Claude, GPT, Gemini, or another LLM. It focuses on Jev.

### Correction 2: No custom comparison bots

The project does not create its own rule-based or competing AI bots for the initial scope. Existing provided players may be used as external/local test opponents.

### Correction 3: No-opponent assumption was wrong

The project does not need to invent a local opponent merely because it runs locally. The primary showcase uses public matchmaking. Local provided players are used for controlled evaluation.

### Correction 4: Human challenge is not a bot

A human challenge means playing a person. It is optional future qualitative evidence, not the current provided-bot benchmark.

### Correction 5: Showdown has a leaderboard, not fixed difficulty levels

The public ladder provides ratings and matchmaking, but not fixed easy/medium/hard opponent progression. The staged progression belongs in the local evaluation harness.

### Correction 6: Raw JSON is not the primary presentation

Technical information should be understandable in the primary experience, with
raw structured data available through an inspection path and local logs. The
specific visual representation is intentionally undecided.

### Correction 7: Transparency does not mean fabricated reasoning

Everything observable should be shown, but the project must not invent hidden reasoning that Jev does not return.

## 16. Current agreed direction

The current direction is:

~~~
Local clone-and-run project
    ↓
Start Jev Battle button
    ↓
Public Gen 9 Random Battle matchmaking
    ↓
poke-env receives battle state
    ↓
deterministic facts and legal actions are rendered
    ↓
Jev returns a typed decision
    ↓
dashboard shows confidence and probabilities
    ↓
legal action is submitted
    ↓
battle result is rendered
~~~

Alongside this public showcase path, a local controlled mode will use existing poke-env reference players for reproducible checks.

No implementation plan has been approved or written yet.

## 17. Still unresolved discussion items

The following items have not been finalized and must not be silently assumed:

- exact local installation details and dependency versions;
- exact number of battles per controlled difficulty tier;
- the minimum numerical threshold that will count as good winning performance;
- the final colors, typography, Pokémon art assets, and dashboard branding;
- which external strong bot, if any, will be used in a future improvement;
- whether public ladder automation is acceptable for a larger future evaluation volume under current Showdown policy.

These are discussion items, not implementation decisions.

## 18. Refined understanding of the harness and Jev boundary

The harness is not just the `poke-env` library. It is the complete application boundary around Jev:

~~~
Showdown -> poke-env -> deterministic evaluator -> Jev -> validator -> Showdown
~~~

`poke-env` supplies the real battle state and legal-order interface. The project adds a thin deterministic evaluator that calculates legal candidate actions, type effectiveness, damage ranges, KO estimates, priority/speed facts when knowable, field consequences, switch safety, and Terastallization legality.

Jev is responsible for the qualitative tactical choice among those legal, annotated candidates. Jev should not be asked to calculate the type chart, reproduce the damage formula, parse raw protocol, or invent a Showdown command.

The `poke-env` Gen 9 calculator returns possible damage ranges, but its documentation notes that some edge cases are ignored. The dashboard must therefore label damage as a calculated range or estimate with assumptions, especially when opponent items, abilities, EVs, IVs, or exact stats are unknown.

The information shown to Jev is a compact information-set snapshot containing current public state, field conditions, legal actions, deterministic annotations, and uncertainty markers. The raw protocol transcript and hidden server state are not sent to Jev.

For the MVP, Jev returns a typed action choice, confidence, and probabilities. The adapter validates the answer, maps it to a legal BattleOrder, sends it to Showdown, and uses a legal fallback on provider or validation failure.

## 19. Refined dashboard pipeline

> The authoritative dashboard contract is
> [dashboard-product-contract.md](design/dashboard-product-contract.md). The
> official Showdown renderer owns the complete game UI. Custom history means
> Jev decision history only. Historical visual plans and mockups are retired.

The dashboard should show more than Pokémon input and Jev output. It should visualize the observable project pipeline:

~~~
OBSERVE -> CALCULATE -> PRESENT OPTIONS -> JEV DECIDES -> VALIDATE -> ACT -> RESULT
~~~

The dashboard can show the exact state, question criteria, deterministic facts, Jev response, validation status, submitted action, latency, cost, and resulting battle event. It must not invent or display hidden chain-of-thought that Jev does not return.

The visual should label the origin of information:

- `Showdown state`
- `Calculated by harness`
- `Jev output`
- `Adapter action`

The dashboard should use wording that is transparent about what is actually
observable and must not imply access to hidden reasoning.

## 20. Dashboard refinement feedback

Earlier visual refinement notes are retired. Preserve only the behavioral
decisions: expose real-time decision evidence, distinguish data origins, avoid
fabricated reasoning, respect the official renderer, and keep unrevealed
opponent information unknown. See
[dashboard-product-contract.md](design/dashboard-product-contract.md).

## 21. What “START JEV BATTLE” actually means

The `START JEV BATTLE` button is an application-level orchestration control, not a claim that Pokémon Showdown has a single native “start game” API with no setup work.

Pokémon Showdown has a normal browser client with a home screen, format selection, settings, matchmaking, battle rooms, and other user-facing controls. A human can use that interface to select a format and start a search. Our agent does not need to automate clicks in that browser interface. It can use the Showdown WebSocket protocol through `poke-env` and perform the equivalent actions programmatically.

For the first public showcase, clicking the button means:

1. Validate local configuration, including the Jev/OpenCode route and Showdown account settings.
2. Connect the agent to the Showdown server through the asynchronous `poke-env` connection.
3. Authenticate or rename the configured Showdown account as required by the public server.
4. Select the fixed target format: Gen 9 Random Battle (`gen9randombattle`). Random Battle does not require the user to build or upload a team.
5. Start ladder matchmaking and wait for Showdown to return a battle room.
6. Detect the battle-start event and initialize the local battle state/dashboard.
7. Enter the turn loop: receive a legal choice request, prepare the Jev input, wait for Jev, validate the typed choice, submit the legal order, and render the result.
8. Stop the search and close or reset the battle session when the battle ends.

The button should therefore show visible startup states rather than jumping immediately from idle to a Pokémon battlefield:

~~~
READY
  -> CONNECTING TO SHOWDOWN
  -> AUTHENTICATING
  -> SELECTING GEN 9 RANDOM BATTLE
  -> SEARCHING FOR OPPONENT
  -> MATCH FOUND
  -> INITIALIZING BATTLE
  -> JEV PLAYING
~~~

This startup sequence is part of the real showcase. The audience should understand that Jev is being connected to a live game environment, not playing a preloaded animation. The dashboard should show a clear error state for connection failure, authentication failure, unavailable format, cancelled search, provider configuration failure, or a battle that ends before the first decision.

The initial dashboard can keep one clear button and one fixed format because the project scope is specifically public Gen 9 Random Battle. A future refinement may expose separate controls for public ladder, human challenge, and controlled local evaluation, but adding a general settings screen is not required for the first showcase.

The important boundary is:

~~~
Dashboard button
    -> application orchestration
    -> Showdown WebSocket / poke-env
    -> real battle room
    -> Jev turn decisions
~~~

The Showdown GUI is not part of the agent's decision loop. The browser dashboard is our visualization and control surface; Showdown remains the game server and protocol endpoint.

Relevant references:

- [Pokémon Showdown protocol: authentication, ladder search, and battle rooms](https://github.com/smogon/pokemon-showdown/blob/master/PROTOCOL.md)
- [poke-env Player documentation, including ladder play](https://poke-env.readthedocs.io/en/latest/modules/player.html)
- [poke-env connection and public-server examples](https://poke-env.readthedocs.io/en/stable/examples/index.html)

## 22. Additional decisions from discussion

The project owner confirmed the following product decisions:

- **Showdown account:** use a dedicated account configured through `.env`. The assistant may attempt account creation during setup; the owner will handle any human-only signup step.
- **Jev failure:** use a legal fallback action when necessary, but make it unmistakable in the dashboard with wording such as `JEV FAILED — FALLBACK USED`. A fallback must never be presented as Jev's decision.
- **Viewer controls:** keep the showcase simple. Viewers should not manually choose moves, switches, or settings. The dashboard exists to observe Jev, not to provide a second human controller.
- **MVP success:** Jev must complete real battles legally and show good winning performance over a meaningful set of battles. A single lucky win is not sufficient; the exact numerical target can be set after baseline measurements.
- **Recording:** keep recording simple. The owner will record the local browser dashboard; no built-in video recording, elaborate replay workflow, or special production system is required for the MVP.
- **Showcase wording:** do not put comparative claim language on the dashboard or in the recorded presentation. Show the behavior and metrics instead.
- **Platform:** prioritize reliable execution on the owner's Windows PC rather than adding cross-platform packaging work.
- **Pokémon assets:** use appropriate Showdown/open-source assets and preserve attribution or licensing notes where required.

## Related documents

- [Phase 0 Jev/OpenCode research](research/phase-0-jev-opencode.md)
- [Phase 1 research and architecture](research/phase-1-research-and-architecture.md)
