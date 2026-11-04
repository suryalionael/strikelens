# 0005. Fighter hotkeys: Q for red, W for blue

- **Status:** accepted
- **Date:** 2026-11-04
- **Issue:** #8

## Context

Every tag needs a fighter: red or blue corner. The analyst switches fighter many
times a round, so the keys must be fast and impossible to confuse with the weapon,
outcome, and target keys. The original brief suggested `R` for red and `B` for
blue, but `B` is already Blocked.

## Options

- `Q` = red, `W` = blue. Both under the left hand, next to each other, not used
  for anything else.
- `R` = red, `B` = blue, and move Blocked to another key such as `O`. Natural
  letters, but Blocked gets a key nobody would guess.
- `R` = red, `Shift+B` = blue. Inconsistent, and `Shift+B` is easy to mistype as `B`.
- One toggle key. Fewer keys, but the analyst has to look at the screen to know
  which fighter is active.

## Decision

`Q` selects red and `W` selects blue. The owner made this call; Freefly is not
contacted until Phase 4.

## Consequences

- The left hand picks the fighter, the right hand picks weapon and outcome, and the
  number keys in between pick the target.
- `R` and `B` stay unambiguous: `B` is only Blocked.
- All keys live in one config object in `apps/tagger/src/tagging/hotkeys.ts`, so a
  later settings screen can rebind them without touching the engine.
