# 0006. Kit and referee colour thresholds calibrated on Byon footage

- **Status:** accepted
- **Date:** 2026-11-07
- **Issue:** #19, #20

## Context

Tracking decides two things from the colours on a person's chest (`track/kit.py`,
`track/referee.py`):

- **Kit:** in Tryout fights the red corner wears a red singlet and blue a blue one.
- **Referee:** Byon referees wear black, so a mostly dark chest is the referee.

The first thresholds were guesses. On the first real run (Tryout 2, Aditya vs
Franky, round 1), only 3 of 12 sampled frames had both boxes right. The referee
was boxed as a fighter in about half of them.

## Measurement

Boxes were labelled by hand on sampled frames from two fights: 12 frames of
Tryout 2 (fighters in red and blue singlets) and 12 frames of a 160 s excerpt of
round 1 of Madness 4, Waruwu vs Londo (shirtless fighters). That gave 9 red
singlets, 8 blue singlets, 17 shirtless fighters, 16 referees, and 25 people in
the crowd. Boxes covering two people were left out.

Chest pixels, medians per class:

| Class | Hue | Saturation | Brightest channel (p25 / p50 / p75) |
|---|---|---|---|
| Red singlet | 336 | 0.56 | 149 / 168 / 186 |
| Blue singlet | 229 | 0.66 | 137 / 164 / 186 |
| Referee | 232 | 0.45 | 46 / 66 / 92 |
| Shirtless fighter | 20 | 0.33 | 118 / 160 / 194 |

What was wrong:

- **Red started at 345 degrees.** Byon's red singlets sit at about 336, between red
  and magenta, so the red share was near zero even for the red corner.
- **Dark ended at 70.** Under the ring lights the referee's black shirt reaches
  about 90, so only part of his chest counted as dark. The rest, with its navy
  tint (hue 232), counted as blue kit.

Share of dark chest pixels for each value of `dark_max_value` (min / median / max):

| `dark_max_value` | Referee | Red | Blue | Shirtless |
|---|---|---|---|---|
| 70 | 0.05 / 0.70 / 0.98 | 0 / 0.01 / 0.07 | 0 / 0 / 0.03 | 0 / 0.07 / 0.37 |
| 100 | 0.60 / 0.78 / 0.99 | 0 / 0.05 / 0.13 | 0 / 0.05 / 0.16 | 0.01 / 0.11 / 0.37 |

With red from 320 degrees and `dark_max_value` 100, the red minus blue kit share
was +0.31 or more for red singlets, -0.34 or less for blue singlets, and between
-0.16 and +0.16 for shirtless fighters and the referee.

## Decision

- Red kit hues: 0-15 and **320**-360 degrees (was 345).
- `dark_max_value`: **100** (was 70). `min_torso_dark` stays 0.5.
- `min_kit_share`: **0.25** (was 0.3), halfway between the singlets (0.31) and
  everyone else (0.16).

On the labelled boxes:

| | Before | After |
|---|---|---|
| Referees removed | 11 of 16 | 16 of 16 |
| Fighters wrongly removed | 0 of 34 | 0 of 34 |
| Kit right (red, blue, or none for shirtless) | 25 of 34 | 34 of 34 |

## Consequences

- These numbers come from the same boxes the thresholds were picked on, so they
  are optimistic. The overlay review of a full round is the real check.
- Two events and one lighting setup each. A new event, venue, or broadcast look
  should be measured the same way before trusting the defaults.
- The red range now includes deep pink. Pink ring ropes or pink clothing inside
  the chest band can count as red kit.
- People in the crowd in dark clothes are now often dropped as referees. That is
  harmless: they are not fighters either.
- Revisit when a corrections file gives the swap and referee numbers for #19 and
  #20 on a whole fight.
