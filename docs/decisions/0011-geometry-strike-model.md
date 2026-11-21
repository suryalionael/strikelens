# 0011. A geometry strike model, ported from mma-vision, kept opt-in

- **Status:** accepted
- **Date:** 2026-11-20
- **Issue:** #81

## Context

The motion baseline (ADR 0009) flags any fast movement and guesses no weapon,
outcome, or target. On the first real fight most of its suggestions were footwork,
feints, or the fighter being hit, and the analyst still pressed every key.

[mma-vision](https://github.com/BinyamAbraha/mma-vision) by Binyam Abraha detects
strikes in MMA broadcast video with rules over both fighters' poses: a wrist or
ankle moving fast toward the opponent, extended at impact, having travelled, with
the foot lifted for a kick; landed if the tip reaches the head, body, or legs or the
head snaps. It is AGPL-3.0 like StrikeLens (stated in its README; the repo has no
licence file yet), and the author agreed to the reuse.

## Decision

Port the detector and its keypoint cleanup to `cv/strikelens_cv/strikes/geometry.py`
as `model = "geometry"`, credited in the module, the CV README, and here. Changes in
the port:

- Plain Python, no numpy, so the rules are tested in CI (which installs no extras).
- Thresholds in torso-heights per second and milliseconds instead of frames, so they
  work at any frame rate. His values (about 30 fps) were converted:
  0.16 torso/frame became 4.8 torso/s, 6 frames became 200 ms, and so on
  (`configs/geometry.toml`).
- MediaPipe's 33 landmarks instead of COCO-17 (the 17 used exist in both).
- Weapon prefill: jab from the lead hand, cross from the rear, or kick. Outcome:
  landed or missed (it cannot see a block). Target: head, body, or legs.
- Every candidate and the gate that rejected it goes to `strike-candidates.json`.

It stays **opt-in**. `infer.toml` keeps `motion-baseline` as the default.

## Measured

Madness 5, round 1, against the analyst's 20 confirmed and 42 rejected tags (a match
is the same fighter within 0.7 s) and Freefly's round 1 landed counts (Meven 19,
Topnoi 10):

| Run | Strikes kept | Confirmed found | Rejected moments flagged | Punch vs kick right | Landed call right | Landed Meven / Topnoi |
|---|---|---|---|---|---|---|
| 10 fps, ported thresholds | 30 | 7 of 20 | 15 of 42 | 4 of 7 | 1 of 7 | 8 / 3 |
| 10 fps, best of 24 settings | 77 | 12 of 20 | 24 of 42 | n/a | 2 of 12 | 19 / 15 |
| 30 fps, ported thresholds | 86 | 9 of 20 | 22 of 42 | 3 of 9 | 6 of 9 | 27 / 31 |
| 30 fps, lower speed thresholds | 107-136 | 8-9 of 20 | 23 of 42 | 1-2 of 9 | 5-6 of 9 | 31-43 / 37-49 |

The 30 fps run used a 3.5-minute cut of round 1, re-tracked; its corners agree with
the verified 10 fps tracks on 92% of frames.

It finds about half the confirmed strikes while flagging about half the moments the
analyst rejected, its punch-or-kick call is no better than a coin, and it counts
Topnoi landing three times what Freefly did. Neither a higher frame rate nor the
thresholds tried fix that. Likely reasons, from the candidate log: low kicks rarely
lift the foot 0.3 torso-heights above the standing ankle (153 candidates dropped
there), keypoints are missing for 20-35% of frames behind the ropes and in the
clinch, and the rules were tuned on one MMA camera angle. Twenty confirmed tags are
also too few to tune on without fitting noise.

## Consequences

- No change for the analyst: suggestions stay on the motion baseline, and the
  prefilled fields are not switched on while they are wrong this often.
- The port, its tests, and the candidate log are the base for tuning once a full
  round is tagged, and its features (reach, extension, travel, distance to the
  target, opponent reactions) feed the trained model and the opponent-aware
  windows (#24, #75).
- Revisit with a fully tagged round: tune `geometry.toml` on rounds 1 and 2,
  measure on round 3.
