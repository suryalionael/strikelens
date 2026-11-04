# Stat definitions

This page defines every v1 stat: formula, inputs, and edge cases. Code lives in
`apps/api/app/stats/core.py` as pure functions with tests.

**Rule:** we do not invent counting rules. Where a rule is not settled, this page
says so and lists it under [Open questions for Freefly](#open-questions-for-freefly).
Until Freefly answers, the code follows the **provisional** rule written here, and
the stat card should say the definition is provisional.

## Coverage

| Stat | How it's produced in v1 | Later goal |
|---|---|---|
| Fight time, round splits | Automatic (round start/end marked once) | Automatic round detection |
| Fighter tracking, ring position, pressure | Automatic (CV) | Same |
| Strike attempts | CV suggests, analyst confirms | Mostly automatic |
| Strikes per minute, per round | Calculated from confirmed attempts | Same |
| Weapon (punch, kick, knee, elbow) | CV suggests, analyst confirms | Mostly automatic |
| Landed vs missed, accuracy | Analyst tags | CV suggestion |
| Target (head, body, legs) | Analyst tags | CV suggestion |
| Defensive responses | Analyst tags | Research stretch |

## Inputs

All stats are calculated from two inputs:

- **Tags** that match `shared/schema/tag.schema.json`.
- **Rounds** from the fight record: `number`, `start_ms`, `end_ms` in video time.

Common filter, applied to every stat below: **only tags with `status: "confirmed"`
count.** Pending and rejected tags are ignored. `source` does not matter: a
confirmed CV suggestion counts the same as a human tag.

Stats are always calculated **per fighter**. Totals across both fighters are only
shown where stated.

A confirmed tag also has to sit inside its round: its `round` must be a marked
round, and its `timestamp_ms` must fall between that round's start and end marks
(inclusive). Confirmed tags that fail this, for example after the bell or after a
round mark was moved, are not counted. `GET /fights/{id}/stats` reports how many
there are as `uncounted_tags`, so the tagger can warn about them.

All of this is `fight_stats(tags, rounds, scheduled_rounds)` in `core.py`, served
by `GET /fights/{id}/stats`. The response also lists the provisional rules below,
so the stat cards can flag them.

## Time

### Round time

```
round_time_s(r) = (r.end_ms - r.start_ms) / 1000
```

The analyst marks start and end once per round (issue #7). Round time is the time
between those marks, not the scheduled round length.

### Fight time

```
fight_time_s = sum(round_time_s(r) for r in rounds)
```

Edge cases:

- **Fight ends early** (stoppage): the last round ends where the analyst marks it,
  so fight time is shorter than scheduled. No adjustment.
- **Pauses inside a round** (referee break, doctor check, foul): provisional rule is
  to include them, because v1 only marks round start and end. Open question for
  Freefly. If they exclude pauses, the tagger needs pause marks.
- **Replays and non-fight segments** inside a round: excluded from tagging. Whether
  they need to be subtracted from round time depends on whether the broadcast cuts
  them in live or after the round. Revisit in issue #18.
- **Round with end before start or overlapping rounds:** invalid input; the API
  rejects it.

Implemented: `round_time_s(round)` and `fight_time_s(rounds)` in `core.py`.

## Attempts

```
attempts(fighter) = count(tags where fighter = f)
attempts(fighter, round) = count(tags where fighter = f and round = r)
```

An attempt is one tag. Landed, missed, and blocked strikes are all attempts.

Implemented: `split(tags, time_s)` and `attempts_by_round(tags)` in `core.py`.

Not settled: **what counts as one attempt inside a combination.** Provisional rule:
every distinct strike in a combination is its own attempt (a jab-cross-hook is
three attempts). Open question for Freefly.

## Landed

```
landed(fighter) = count(tags where fighter = f and outcome = "landed")
```

Not settled: **what counts as landed.** In particular, a strike that hits the guard
or a checked leg kick. Provisional rule: those are `blocked`, not `landed`. Open
question for Freefly.

## Accuracy

```
accuracy = landed / attempts
```

- Range 0.0 to 1.0. Displayed as a percentage with one decimal (32.7%).
- **Zero attempts:** accuracy is undefined. The function returns `None` and the UI
  shows a dash. It never shows 0%.
- `landed > attempts` is impossible and raises an error.
- Blocked strikes count as attempts that did not land, so they lower accuracy.
  This follows from the provisional landed rule.

Implemented: `accuracy(landed, attempts)` in `core.py`.

## Strikes per minute

```
strikes_per_minute = attempts / (fight_time_s / 60)
```

- Provisional rule: uses **attempts**, not landed. We do not know which one Freefly
  uses (open question).
- **Zero fight time:** undefined. Returns `None`.
- Per round: `attempts(f, r) / (round_time_s(r) / 60)`.
- Across several fights: total attempts divided by total fight time (not the
  average of each fight's rate). Provisional; confirm with Freefly.

Implemented: `strikes_per_minute(attempts, fight_time_seconds)` in `core.py`.

## Per-round splits

For each round and fighter: attempts, landed, accuracy, strikes per minute. Same
formulas as above with the round filter applied.

- **Partial round** (stoppage mid-round): show the real values. The per-round
  strikes per minute uses the shortened round time, so it stays comparable. Raw
  attempt counts for that round are lower simply because the round was shorter;
  the stat card should mark the round as partial.
- **How a round is detected as partial** (provisional): when fewer rounds are
  marked than scheduled, the last marked round is partial. The fight record has no
  stoppage time yet, so this is the only signal. Known limit: while the analyst is
  still marking rounds, the latest round is flagged too. Implemented:
  `partial_rounds(rounds, scheduled_rounds)`.
- **Tags outside every round** (for example, after the bell): not counted. The
  tagger warns the analyst.

## Weapon mix

```
weapon_share(f, w) = count(tags where fighter = f and weapon = w) / attempts(f)
```

- Calculated on **attempts**. Also show landed by weapon.
- Shown both per weapon (jab, cross...) and per group (punch, kick, knee, elbow).
  Groups are in [tag-schema.md](tag-schema.md#weapons).
- Zero attempts: undefined for every weapon.

Implemented: `weapon_mix(tags)` and `weapon_group_mix(tags)` in `core.py`.

## Target distribution

```
target_share(f, t) = count(tags where fighter = f and outcome = "landed" and target = t) / landed(f)
```

- Provisional rule: target distribution is calculated on **landed** strikes, because
  for missed strikes the target is a guess at intent. Also keep the attempts-based
  version available. Open question for Freefly which one they publish.
- Zero landed: undefined.

Implemented: `target_distribution(tags, "landed" | "attempts")` in `core.py`.

## Defensive responses

Not defined in v1. The tag schema has no defence fields yet. Before adding any,
we need Freefly's list of defensive actions they track (if any). Tracked in the
open questions.

## CV-only stats

**Ring position** and **pressure** come from fighter tracking (issues #19-#22).
Definitions (for example, "pressure = share of time a fighter moves forward while
the other moves back") will be proposed in Phase 2 and added here. They are new
stats, so they need Freefly's agreement before they appear on a public card.

## Reference fixture

Freefly published these figures for **Nelson Julianto across 5 fights**:

| Figure | Value |
|---|---|
| Attempts | 608 |
| Landed | 199 |
| Strikes per minute | 15.89 |
| Round 1 attempts | 249 |
| Round 3 attempts | 140 |
| Accuracy (derived: 199 / 608) | 32.7% |

These are **Freefly's published figures**, used only as a sanity check in
`apps/api/tests/test_stats_core.py`. They are not our own count. The implied fight
time is 608 / 15.89 = 38.3 minutes across the 5 fights; we have not checked that
against the fights themselves.

## Open questions for Freefly

Status of each is tracked in issue #5. We ask Freefly at the start of Phase 4,
once the tool works end to end (see [roadmap.md](roadmap.md#when-we-contact-freefly)).
Do not resolve these in code without an answer.

1. **How do you define a landed strike?** Does a strike on the guard count? A
   checked leg kick? A kick that lands on the arm covering the body?
2. **What counts as one attempt in a combination?** Is a jab-cross-hook three
   attempts or one?
3. **Which stats take you longest to count today?** This decides what we automate first.
4. **Can you share one fight you have already counted, with your numbers?** Gate 1
   (issue #16) uses their published numbers instead, so this is for checking stats
   they do not publish.
5. **Do you want the tool private to your team or public?**

Further questions raised while writing these definitions:

6. Is strikes per minute based on attempts or on landed strikes? And over several
   fights, is it total attempts over total time, or an average of per-fight rates?
7. Do you include pauses (referee breaks, doctor checks) in fight time?
8. Is target distribution based on landed strikes or on all attempts?
9. Do you separate any strike types beyond jab, cross, hook, uppercut, kick, teep,
   knee, elbow (for example backfist, spinning strikes, sweeps)? Does Byon allow elbows?
10. Do you track defensive actions (blocks, checks, slips, clinches)? If so, which?
11. Do clinch strikes (knees in the clinch) count the same as strikes at range?
