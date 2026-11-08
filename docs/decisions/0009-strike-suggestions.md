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

## Consequences

- The whole loop from keypoints to reviewed tags runs today.
- Precision and recall of the baseline are unknown. It reacts to any fast movement,
  such as footwork or a clinch, and may miss slow strikes. Do not quote its numbers.
- #24 must beat it on per-weapon precision and recall, and #28 measures the result.
- The threshold and gap should be set from tagged fights once they exist.
