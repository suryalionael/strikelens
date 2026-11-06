# Fight rules (UCC Kickstriking)

Byon Combat fights under the **Kickstriking** rules of the UNI COMBAT COUNCIL
(UCC): the *Kickstriking Official Holy Book v1 (2025)*, at
<https://unicombatcouncil.com/rules/>. Read 2026-11-05.

This page is a short summary in our own words, for building StrikeLens. The
rulebook is the source. If the two disagree, the rulebook wins, and this page needs
fixing.

## What the rules settle

These tell us what can happen in a fight, so the tag schema can describe it.

- **Rounds:** 3 minutes, with 1 minute of rest. The UCC sets the number of rounds
  for each bout. A tied fight goes to one extra round, the Judgement Round.
- **Legal punches:** the front of the fist, the backfist, and the spinning
  backfist, to the head and upper body.
- **Legal kicks:** with the instep, shin, or sole (push kick), to the head, body,
  and legs. Push kicks go from the abdomen up. Calf kicks are legal. Oblique
  kicks below the waist are not.
- **Knees:** legal to the head and body, without pulling the head.
- **Elbows:** slicing elbows are legal. Downward (12-6) elbows are not.
- **Spinning and flying strikes:** legal. The rules group them as "advanced
  techniques" (for example spinning backfist, spinning head kick, flying knee).
- **Illegal targets:** the back of the head, the throat, the back of the body,
  and the groin.
- **Clinch:** short. It allows one strike and must then be released. Long
  clinches to rest are a foul.
- **Catching:** only kicks can be caught. A catch allows one strike, then the
  leg must be let go.
- **No throws, sweeps, or takedowns.**
- **Knockdowns:** the rules define a knockdown (a legal strike makes a fighter
  touch the canvas with anything but the soles of the feet, or the ropes hold
  them up) and say the referee alone decides it. Several knockdowns can end a
  bout.

## What the rules do not settle

The rules say how **judges score a round**: a 10-point must system, with clean
strikes and damage first, then aggression, ring control, and defence. A "clean
strike" in the rules is a judging idea.

They do not say how to **count** strikes for stats: what one attempt is, whether
a strike on the guard has landed, or how to split weapons into categories. Those
are Freefly's counting rules, and they stay open questions in
[stat-definitions.md](stat-definitions.md#open-questions-for-freefly) until
Freefly answers. Do not turn a judging rule into a stat definition.

## What this means for StrikeLens

- **Weapons:** the tag schema has no backfist and no way to mark a strike as
  spinning or flying. Both are legal in Byon fights. Whether to add them depends
  on how Freefly counts them (open question 9). See [tag-schema.md](tag-schema.md#weapons).
- **Elbows** are legal, so the `elbow` weapon stays.
- **Clinch strikes** are limited to one per clinch, so they are rarer than in
  Muay Thai. Whether they count the same as strikes at range is still open
  question 11.
- **Knockdowns** are well defined here. StrikeLens does not tag them yet (open
  question 13).
- **Round time:** analysts mark each round's start and end by hand, so the
  3-minute rounds and the Judgement Round need nothing special.
