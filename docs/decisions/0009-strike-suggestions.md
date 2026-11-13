# 0009. Strike suggestions: peaks in a score, with a motion baseline first

- **Status:** accepted (starting values, to revisit with the trained model in #24)
- **Date:** 2026-11-08
- **Issue:** #25

## Context

Suggestions need a model, and the trained one (#24) needs tagged fights that do not
exist yet. The review mode (#26) and the pipeline around it can be built and tried
without it.

## Decision

- A model scores a window (the same shape as training, ADR 0008) every 100 ms for
  each fighter. Peaks at or above a threshold, at least a minimum gap apart, become
  pending tags. Models plug in behind one small interface.
- Until #24, the model is `motion-baseline`: a logistic curve of the peak speed of
  the elbows, wrists, knees, and ankles, in box heights per second. No training, no
  weapon guess.
- Threshold 0.9 and gap 700 ms. There are no tagged strikes to calibrate against, so
  these were chosen only by how many suggestions they give: on the Tryout 2 rounds,
  about 24 a minute for both fighters, against 84 a minute at 0.6 and 400 ms.

## Update: one suggestion per moment, 50 per round (#72)

On the first real fight (Madness 5, 3 rounds), the baseline gave about 140 suggestions
per round, against Freefly's 85 attempts per round for both fighters together, and
often suggested both fighters at the same instant. Reviewing that was slower than
tagging. After peak picking, suggestions closer than `merge_gap_ms` (1000), of either
fighter, are now merged (the most confident is kept), and each round keeps at most
`max_per_round` (50), counting suggestions still waiting for review. No suggestion is
placed within `merge_gap_ms` of a tag already in the fight. The cost: the second
strike of a fast combo, or a counter within a second, is not suggested and is added
by hand. Both numbers are for review time, not accuracy, and should be revisited
with #28.

## Consequences

- The whole loop from keypoints to reviewed tags runs today.
- Precision and recall of the baseline are unknown. It reacts to any fast movement,
  such as footwork or a clinch, and may miss slow strikes. Do not quote its numbers.
- #24 must beat it on per-weapon precision and recall, and #28 measures the result.
- The threshold and gap should be set from tagged fights once they exist.
