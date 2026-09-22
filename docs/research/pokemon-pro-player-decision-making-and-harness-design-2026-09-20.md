# Pokémon Expert Decision-Making and Harness Design Research

**Date:** 2026-09-20  
**Project:** `pokemon-showdown-jev-agent`
**Purpose:** Explain how strong competitive Pokémon players make decisions and translate that thinking into the battle harness and the information supplied to Jev AI.

## Scope and important format distinction

This document is about decision-making, not code implementation. It is intended to be standalone for an agent that has no previous conversation context.

The project currently plays Pokémon Showdown `gen9randombattle`, which is Gen 9 Random Battle singles. This matters because “professional Pokémon player” can refer to different formats:

- **VGC:** official competitive doubles. Players use team preview, select a subset of their team, and reason about board positioning, Protect, targeting, redirection, speed control, and best-of-three adaptation.
- **Smogon singles:** usually 6v6 singles with switching, hazards, status, prediction, momentum, win conditions, and long-term resource management.
- **Random Battle singles:** teams are generated automatically with curated competitive sets. Team-building is removed, the opponent’s complete team is not normally known at the beginning, and players must infer sets and preserve answers to unrevealed threats.

The project should borrow general expert principles from both VGC and Smogon singles, but the harness should be designed primarily for Random Battle singles. A VGC strategy should not be copied directly into this project.

## The central correction to the beginner mental model

A beginner often thinks:

> Switch to the Pokémon that counters the opponent, then use the strongest attack, buff, debuff, or status move.

That is part of Pokémon strategy, but it is incomplete. A strong player is solving a longer decision problem:

> Given the known facts and hidden possibilities, which legal action gives me the best chance of reaching a winning position while avoiding my losing position?

The strongest move is not necessarily the move that deals the most immediate damage. It may be a switch, recovery move, status move, setup move, hazard, speed-control move, pivot, scout, or even a deliberate sacrifice.

## How strong players think

### 1. They identify a win condition

A **win condition** is the concrete way the player expects to win. Examples include:

- Setting up a sweeper after removing its checks.
- Preserving one defensive Pokémon that blocks the opponent’s main threat.
- Wearing the opponent down with hazards and status.
- Keeping a powerful attacker healthy until the opponent’s defensive Pokémon are weakened.
- Creating a late-game speed or priority advantage.
- Winning a resource battle through recovery, PP, or superior remaining Pokémon.

The player asks:

- Which of my Pokémon can eventually win?
- What must happen before that Pokémon can win?
- Which opposing Pokémon prevents that plan?
- Which of my Pokémon must remain alive and healthy?

### 2. They identify a lose condition

A **lose condition** is what the opponent can do that makes winning unlikely or impossible. Examples:

- An opposing sweeper can boost once and outspeed the entire team.
- One Pokémon is the only reliable answer to a dangerous attacker.
- The team cannot break an opposing wall.
- The opponent can obtain a free setup turn after a predictable KO.
- A specific unrevealed move, ability, item, or Pokémon invalidates the current plan.

The player does not blindly take a KO if that KO gives the opponent a free setup opportunity or removes the only Pokémon capable of stopping the opponent’s endgame.

### 3. They evaluate threats, not only type matchups

Type advantage is useful, but “counter” is not always a complete or safe concept. A Pokémon may resist an opponent’s obvious attack but lose to coverage, status, setup, hazards, or an item.

For each important opposing Pokémon, an expert considers:

- What can it do immediately?
- Can it knock out or cripple the active Pokémon?
- Can it set up?
- What moves, abilities, or items are still possible?
- What can safely switch into it?
- What happens if the opponent predicts the switch?
- Is it more important to damage it, status it, force it out, or preserve a specific answer?

### 4. They switch for position and momentum

A switch is good when it improves the future position, not merely because the new Pokémon has a favorable type.

Before switching, a strong player considers:

- Whether the incoming Pokémon survives the likely attack.
- Whether it is vulnerable to unrevealed coverage.
- Entry-hazard and status costs.
- Whether the switch preserves a critical team resource.
- Whether the new Pokémon threatens the opponent or only passively survives.
- What happens if the opponent stays in.
- What happens if the opponent also switches.

Players may also use a **double switch**: switching while expecting the opponent to switch, in order to place the correct attacker against the opponent’s expected answer.

### 5. They look for progress

Progress means improving the overall winning position, even without a knockout. Progress may come from:

- Direct damage.
- Status conditions.
- Entry hazards.
- Removing or revealing an item, ability, or move.
- Lowering speed or controlling turn order.
- Forcing a switch.
- Creating a safe setup turn.
- Bringing in a dangerous attacker safely.
- Making an opponent’s future switches expensive.

The best action is often the one that makes reliable progress while giving the opponent the fewest good responses.

### 6. They manage risk and reward

Expert players do not attempt a prediction every turn. They choose between a safe line and an aggressive prediction based on the position.

They prefer safety when:

- They are already winning.
- The opponent has no strong comeback route.
- The reward for predicting correctly is small.
- A failed prediction loses a critical Pokémon or win condition.

They accept risk when:

- The safe line is already losing.
- Only a narrow sequence can recover the game.
- The reward is large enough to justify the risk.
- The opponent has been conditioned to expect the obvious action.

This means the harness must distinguish “high risk because it is foolish” from “high risk because it is necessary.”

### 7. They think short-term and long-term

For every action, strong players consider both the current turn and the likely next turns:

- What happens after this Pokémon is knocked out?
- What can the opponent send in for free?
- What can I safely bring in afterward?
- Does this attack put the opponent into a future KO range?
- Does this setup move create a sweep, or merely waste a turn?
- Does this switch preserve my endgame plan?

A move that looks good immediately can be bad if it loses the next three turns.

### 8. They manage resources

Pokémon is a resource-management game. Important resources include:

- HP.
- Number of healthy Pokémon.
- Recovery PP and offensive PP.
- Status condition.
- Boosts and drops.
- Terastallization or another once-per-battle mechanic.
- Revealed moves, items, abilities, and speed information.
- Remaining checks, counters, pivots, and revenge killers.

A Pokémon at low HP may still be valuable if it can absorb one specific attack, provide a safe switch, or revenge-kill a key threat. Conversely, a full-health Pokémon may be expendable if sacrificing it gives the actual win condition a safe entrance.

### 9. They value speed control and turn order

Speed is not only the displayed Speed stat. Strong players reason about:

- Current speed order.
- Speed boosts and drops.
- Priority moves.
- Paralysis.
- Tailwind, Trick Room, and similar effects.
- Choice Scarf and other speed-changing items.
- Whether a speed-control action creates a guaranteed knockout.

Changing who moves first can convert a losing matchup into a winning one. Therefore, speed information and speed-control opportunities must be explicit in the decision state.

### 10. They gather information and update beliefs

Every observed action gives information about the opponent:

- A revealed move narrows the possible set.
- Damage reveals information about stats, item, ability, or investment.
- Switching patterns reveal priorities and likely checks.
- Refusing to switch may reveal confidence, a setup plan, or an attempt to out-predict.
- A revealed item or ability changes future damage and survival calculations.

In Random Battle, this is especially important because the full opposing team and set are not known in advance. The player must maintain possibilities rather than pretending that an unconfirmed move, item, or ability is certain.

## What this means for the current project format

The project’s Random Battle agent should emphasize:

1. Set and move inference from observed behavior.
2. Preserving answers to unknown opposing Pokémon.
3. Recognizing whether a revealed Pokémon is offensive, defensive, supportive, or a setup threat.
4. Calculating exact or ranged outcomes instead of using only a rough damage score.
5. Evaluating switches against likely coverage, not only the visible attack.
6. Identifying which of our Pokémon is the endgame win condition.
7. Recognizing when a Pokémon is expendable and when it must be preserved.
8. Using safe progress when ahead and calculated risk when behind.

## Translation into harness responsibilities

The harness should transform the battle into several distinct layers before asking Jev for a decision.

| Expert concept | Harness should provide | Jev should judge |
|---|---|---|
| Current state | Exact turn, active Pokémon, HP, status, boosts, field effects, hazards, weather, and terrain | What matters most right now |
| Legal choices | Every legal move, switch, Tera option, and relevant order | Which legal choice is strategically best |
| Win condition | Candidate endgame plans and the steps needed to reach them | Which plan should be pursued |
| Lose condition | Threats and sequences that can cause a likely loss | Which danger must be handled first |
| Hidden information | Possible moves, items, abilities, speed tiers, Tera types, and confidence levels | How much uncertainty changes the decision |
| Mechanics | Damage ranges, KO probabilities, survival probabilities, speed order, accuracy, and status effects | Whether the outcome is worth the risk |
| Switching | Entry damage, likely survival, momentum, coverage risk, and future options | Whether switching improves the position |
| Resources | Important HP totals, remaining checks, recovery, PP, and once-per-battle mechanics | What must be preserved or spent |
| Future consequences | Likely opponent responses and next-turn positions | Which action has the best continuation |
| Information gain | What each action may reveal | Whether scouting is worth giving up immediate progress |

The harness should be the source of mechanical truth. Jev should be the strategic evaluator. Jev should not have to reconstruct Pokémon mechanics from vague text or incomplete snapshots.

## Recommended information supplied to Jev

The decision state should contain more than raw battle facts. It should include a structured strategic brief:

- Format and objective.
- Current battle phase: opening, information gathering, midgame, endgame, or emergency recovery.
- Exact visible state.
- Legal candidate actions.
- Our likely win conditions.
- Our immediate lose conditions.
- Critical Pokémon and resources that must be preserved.
- Opponent threat ranking.
- Hidden-information hypotheses with confidence, not unsupported certainty.
- For every candidate action:
  - purpose;
  - expected damage or effect;
  - KO and survival probabilities;
  - likely opponent responses;
  - best-case, likely-case, and worst-case results;
  - effect on the win condition;
  - effect on information and future options.

Jev should then rank the legal action IDs, not invent an action outside the candidate list.

## Jev limitation: Pokémon meaning must be translated explicitly

The harness must not assume that Jev already understands Pokémon as a game domain. Jev is a structured decision model, not a Pokémon simulator, rules engine, or conversational tutor. Its public contract is state plus typed questions and typed answers; it does not guarantee complete knowledge of Pokémon mechanics, the current Pokémon metagame, or the meaning of competitive terms.

Jev may have some general or learned Pokémon knowledge, but that knowledge must be treated as unreliable. The safe design assumption is:

> Jev can compare the options and consequences represented in the supplied state, but the harness must explicitly provide the Pokémon meaning needed for a correct decision.

The harness must therefore act as a Pokémon-to-decision translation layer. It should not send only a species name and move name and expect Jev to reconstruct their meaning.

| Pokémon concept | Meaning that should be supplied to Jev |
|---|---|
| Move | Effect, damage range, accuracy, priority, status, boosts, target, and resource cost |
| Type matchup | Numerical effectiveness, immunities, STAB, and expected damage |
| Counter | Whether the Pokémon survives likely attacks and threatens a KO or favorable progress |
| Setup move | Exact stat changes, required survival, and expected future payoff |
| Hazard | Damage or status applied when switching in |
| Status | Current effect and estimated future impact |
| Speed | Estimated turn order, priority, boosts, drops, and uncertainty |
| Switch | Entry damage, survival chance, coverage risk, and resulting position |
| Prediction | Opponent response probabilities and consequences of being wrong |
| Win condition | A concrete plan and the steps required to achieve it |
| Lose condition | A concrete opponent sequence that can defeat us |
| Momentum | How the action changes useful future options and safe entries |
| Pokémon meta | Explicit set hypotheses and observed statistics, not assumed knowledge |

For example, the harness should not provide only `swords_dance`. It should describe the action as a setup action with zero immediate damage, a two-stage Attack increase, a requirement that the user survive the opponent’s next action, a risk of being knocked out or disrupted, and a potential payoff of improved future KO probabilities.

Likewise, the harness should not merely say that a Pokémon is a “counter.” It should provide the evidence: expected damage received, survival probability, attacks that threaten a KO, coverage risks, hazard cost, and what the switch enables afterward.

### Division of responsibility

The harness should calculate and explain mechanical truth:

- legal actions;
- exact move effects;
- damage ranges;
- KO and survival probabilities;
- type effectiveness and immunities;
- speed order and priority;
- status and hazard effects;
- possible switches;
- possible opposing sets and their confidence;
- Terastallization consequences; and
- accuracy and random-outcome effects.

Jev should judge the strategic choice among those accurately described outcomes:

- which threat matters most;
- whether to attack, switch, set up, recover, status, scout, or sacrifice;
- whether the current position calls for safety or calculated risk;
- which Pokémon or resource must be preserved;
- which win condition is realistic; and
- which legal action has the best overall winning outlook.

Jev should not be expected to independently recreate the Pokémon battle engine from incomplete prose.

### Competitive vocabulary must be made concrete

Terms that are obvious to an expert human are not safe as unexplained instructions to Jev. The harness should translate them into observable consequences:

- **Preserve the check:** this Pokémon is currently the only known team member with a high survival probability against a specific opposing threat.
- **Gain momentum:** the action is expected to create more favorable legal choices or a safer way to bring in the win condition.
- **Risky prediction:** if correct, estimated win probability rises by a stated amount; if wrong, it falls by a stated amount or loses a critical resource.
- **Force a switch:** the opponent has few or no good stay-in outcomes according to the calculated threat and damage information.
- **Set up:** the action gives a defined boost or field effect and has a calculated chance of surviving long enough to benefit from it.

The state should use both readable descriptions and numerical or categorical facts. Natural-language strategy labels alone are insufficient.

### Hidden information and metagame knowledge

The harness must not assume that Jev knows the opponent’s unrevealed moves, item, ability, speed tier, Tera type, or remaining Pokémon. For Random Battle, it should provide hypotheses such as:

- possible move, item, and ability sets;
- observed evidence for each hypothesis;
- confidence or probability for each hypothesis;
- damage evidence from previous turns;
- likely role, such as offensive, defensive, setup, or utility; and
- how each hypothesis changes the candidate action outcomes.

For example, instead of saying “this is probably defensive,” provide “recovery was observed and damage was low; estimated defensive or utility set probability is 65%, offensive set probability is 35%.” Jev should reason over uncertainty instead of treating an unconfirmed guess as fact.

### Jev interface constraints

The harness must also respect Jev’s decision-model behavior:

- Jev returns typed answers rather than a normal free-form explanation.
- Choice questions should contain the actual legal action IDs.
- Questions are evaluated independently from the supplied state; Jev should not be expected to remember a previous question’s answer.
- Confidence is not the same as the probability that an action wins.
- Jev should not be expected to perform a complete multi-turn Pokémon simulation without the relevant outcomes being represented in the state.
- The action list must remain bounded and meaningful.
- The validator must reject anything that is not legal in the actual battle.

This section is a critical design constraint: the harness is not merely packaging data for Jev. It is compiling Pokémon mechanics and expert concepts into explicit decision features that Jev can compare.

## Suitable Jev decision questions

Because Jev is a typed decision model, strategic questions should be atomic and answerable from the same state. Conceptually, the harness can ask questions such as:

1. Which opponent threat must be handled first?
2. What is our strongest realistic win condition?
3. Which resource is most important to preserve this turn?
4. Is this a safety position, a progress position, a setup position, or an emergency position?
5. Which legal action best maximizes expected win probability?

The final action question should be constrained to the legal candidate IDs. The earlier strategic answers can help telemetry, evaluation, and future state construction, but the validator must always treat the battle engine as authoritative.

## What the harness should not do

The harness should not:

- Reduce the decision to highest base power.
- Treat type advantage as a guaranteed counter.
- Assume unrevealed moves, items, abilities, or Pokémon are known.
- Give Jev only a single rough damage percentage.
- Hide the battle history and revealed information.
- Treat every turn as equally safe for prediction.
- Assume setup is good without checking whether it creates a real winning line.
- Assume a KO is always beneficial.
- Ask Jev to perform exact simulator mechanics that the harness can calculate deterministically.

## Practical example

Suppose the active Pokémon can deal 40% damage but will probably be knocked out afterward.

A simplistic agent attacks because 40% damage is visible.

An expert process asks:

- Can the opponent be knocked out instead?
- Can we switch safely?
- Is the active Pokémon our only answer to another threat?
- Does the opponent get a free setup turn if we attack or switch?
- Can status or speed control change the matchup?
- If we sacrifice this Pokémon, what enters next?
- Does sacrificing it create our win condition?
- Are we currently ahead, or is an aggressive prediction necessary?

The correct action could be an attack, switch, setup move, status move, recovery, or sacrifice. The answer depends on the overall win probability, not immediate damage alone.

## Final design principle

The correct architecture is:

> battle engine truth + hidden-information belief tracking + strategic state construction + Jev ranking + legal-action validation

Jev should be treated as the strategic decision-maker, not the entire Pokémon player. A strong player’s expertise must be represented in the state and candidate evaluation supplied to Jev. The harness therefore needs to understand the battle deeply enough to explain the strategic situation before Jev chooses.

This approach can make Jev more capable of expert-like decisions, but it does not guarantee expert-level performance or an undefeated record. Pokémon contains hidden information and randomness, and even professional players maximize winning probability rather than guaranteeing every battle.

## Research sources

- [Smogon: Getting Started with Competitive Battling](https://www.smogon.com/articles/getting-started) — prediction, switching, progress, risk/reward, and short-term versus long-term planning.
- [Smogon: An Introduction to Prediction](https://www.smogon.com/smog/issue1/introduction_to_prediction) — information gathering, prediction risk, and when risky play is necessary.
- [Smogon: Prediction and Planning: The Art of Decision Making in Ubers](https://www.smogon.com/smog/issue20/prediction_ubers) — planning, backup plans, momentum, and risk/reward.
- [Smogon forum: Pokémon Battling Crash Course](https://www.smogon.com/forums/threads/pok%C3%A9mon-battling-crash-course.3656181/) — scouting, win conditions, lose conditions, pacing, resources, and information management.
- [Smogon: Where’s the Speedometer? A Beginner’s Guide to Speed Control in VGC](https://www.smogon.com/articles/guide-to-speed-control-in-vgc-p1) — speed control and its strategic value.
- [Smogon: Random Formats on Pokémon Showdown](https://www.smogon.com/articles/random-formats-overview) — the role and characteristics of Random Battle formats.
- [Smogon forum: Questions About How Random Battles Formats Work](https://www.smogon.com/forums/threads/questions-about-random-battles-formats-work-read-here.3712694/) — Gen 9 Random Battle generation, roles, and curated random sets.
- [Pokémon: Experience a Pokémon VGC Event in Japan with Regional Champion Joe Ugarte](https://www.pokemon.com/us/features/experience-a-pokemon-vgc-event-in-japan-with-regional-champion-joe-ugarte) — official tournament-level examples of team roles, offensive synergy, defensive pivots, and strategic preparation.
- [Pokémon: Best-of-Three Swiss Rounds Shake Up the Pokémon Video Game Championships](https://www.pokemon.com/us/features/best-of-three-swiss-rounds-shake-up-the-pokemon-video-game-championships) — consistency, surprise, and adaptation in official competitive play.

## Relationship to other project research

This document is intended to be read alongside the project’s existing harness and Jev research documents:

- `showdown-harness-current-system-2026-09-20.md`
- `jev-ai-typesafe-research-2026-09-20.md`

It does not replace those documents. It adds the missing strategic layer: how expert Pokémon decisions should be represented before they are sent to Jev.
