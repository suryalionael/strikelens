# 0008. Training windows: 1 s around the tag, 16 samples, box-normalised

- **Status:** accepted (starting values, to revisit with the first model in #24)
- **Date:** 2026-11-07
- **Issue:** #23

## Context

The strike model reads short sequences of one fighter's keypoints and says whether
a strike happens, and which weapon. Confirmed tags give the time and the weapon.
The tag time is when the analyst pressed the first key, close to the moment of
contact. Keypoints come from the pose stage at the ingest frame rate (10 fps by
default), with missing frames stored as missing.

## Options

- **Window length.** A jab takes about 0.2-0.4 s, and a round kick about 0.5-0.8 s
  from chamber to contact. A short window misses the wind-up of a kick. A long one
  mixes in the next strike of a combination.
- **Where the tag sits.** The analyst tags near contact, so most of the movement
  comes before the tag time.
- **Coordinates.** Image pixels depend on where the fighter stands and how close the
  camera is. Normalising to the fighter's box removes both.

## Decision

- 600 ms before the tag and 400 ms after: 1 s in all, with the tag a little past
  the middle. That covers a kick's wind-up and the follow-through or recoil.
- 16 evenly spaced samples, each from the nearest extracted frame. At 10 fps that
  is about one frame per sample; at 25 fps it keeps the length fixed.
- Keypoints relative to the fighter's box: centre at 0, box height 1. Visibility
  kept. The manifest records the keypoint format and landmark names, so formats
  are never mixed (ADR 0004).
- A window with more than 25% of samples missing is dropped. Missing samples stay
  null, never zeros.
- Negatives: rejected suggestions, plus 2 background windows per strike for each
  fighter, from round time at least 1 s from any tag of that fighter, chosen with a
  seed so a rerun gives the same set.
- Split by whole fight, by a stable hash of the fight name: 20% for validation.

## Consequences

- These are reasoned starting values, not measured ones. #24 should compare at
  least one other length (for example 800 ms before, 400 ms after) and report
  per-weapon recall, then update this ADR.
- 10 fps is coarse for fast punches; if #24 shows that, ingest at 25 fps for
  training fights.
- With few fights, the hash can put all of them in one split. The command says so;
  more fights fix it.
