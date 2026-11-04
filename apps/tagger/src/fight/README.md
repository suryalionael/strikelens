# fight/

Fight setup: create or open a fight, pick or add fighters, and mark where each
round starts and ends in the video. See issue #7.

- `form.ts`: pure validation for the new fight form.
- `rounds.ts`: pure round marking and validation (end after start, no overlap, no
  more rounds than scheduled). A fight that ends early simply has fewer rounds.
- `FightSetup.tsx`: loads fighters and fights from the API, shows the form or the
  open fight.
- `RoundMarker.tsx`: marks rounds at the player's current time and saves them with
  `PUT /fights/{id}` whenever they are valid. A round is saved once it has an end.
