# 0010. The target is optional on a confirmed tag

- **Status:** accepted
- **Date:** 2026-11-13
- **Issue:** #79

## Context

A confirmed tag had to carry a weapon, an outcome, and a target, so every strike
cost the analyst a key for head, body, or legs. Freefly's published fight breakdowns
show attempts, landed, accuracy, and punches, elbows, and knees, but no target
split. On the first real fight (Madness 5), tagging speed was the main complaint.

## Options

- **Keep the target required.** Complete data, one more key on every strike.
- **Guess the target from pose.** No key, but an arm-or-leg guess from the same pose
  data was right on only 9 to 14 of 19 confirmed tags, so a target guess is not
  ready.
- **Make the target optional.** One key fewer when the fight does not need it.

## Decision

A confirmed tag needs a weapon and an outcome. The target may be null. In the
tagger, a target key still saves the tag, and `Enter` saves it without one.

## Consequences

- A strike is two keys and `Enter`, or three keys as before.
- Target distribution covers only strikes that have a target, and is undefined
  when none does. A fight tagged partly with targets gives shares for that part,
  which may not represent the whole fight.
- Training data for target classification (#34) only comes from tags with a target.
- Revisit if Freefly asks for target stats (open question 8).
