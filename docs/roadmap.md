# Roadmap

Five phases, each ending in a gate. A gate is a demo or result that proves the
phase worked. GitHub milestones mirror this table.

Capacity: about 8-10 hours a week.

| Phase | Dates | Gate |
|---|---|---|
| Phase 0 · Setup | 2026-11-03 to 2026-11-08 | Repo, docs, CI green |
| Phase 1 · Tagging app MVP | 2026-11-09 to 2026-11-29 | **Gate 1:** demo to Freefly, one fight tagged and compared with their numbers |
| Phase 2 · CV baseline | 2026-11-30 to 2026-12-13 | **Gate 2:** overlay demo video ready to share |
| Buffer: exams and winter break | 2026-12-14 to 2027-01-03 | No milestone |
| Phase 3 · Strike suggestions | 2027-01-04 to 2027-01-31 | **Gate 3:** assisted tagging works end to end on a full fight |
| Phase 4 · Validate and ship v1 | 2027-02-01 to 2027-02-21 | **Gate 4:** v1 handed over to Freefly |

## Phase 0 · Setup

Issues #1-#5. Repo, docs, CI, practice clips, first contact with Freefly.

The stat definitions question (#5) is blocked on Freefly's reply. Phase 1 can
start without it because the code follows the provisional rules in
[stat-definitions.md](stat-definitions.md).

## Phase 1 · Tagging app MVP

Issues #6-#16. Player, fight setup, hotkey tagging, timeline, edit and undo, API,
stats engine, stat cards, export, and the Gate 1 comparison.

Suggested order: #12 (API) and #6 (player) first, then #7, #8, #9, #10, #11, then
#13, #14, #15, and finally #16.

**Gate 1 pass:** one full fight tagged in StrikeLens, numbers compared with
Freefly's own count for the same fight, and every gap explained (definition
difference or counting error).

## Phase 2 · CV baseline

Issues #17-#22. Ingest, replay filtering, tracking with two stable IDs, referee
filter, pose, overlay.

**Gate 2 pass:** an overlay video of at least one round, with stable fighter boxes
and skeletons, that we are allowed to share (see [data-policy.md](data-policy.md)).

## Buffer (Dec 14 to Jan 3)

Exams and winter break. No planned work. Anything that slipped from Phases 1-2 can
land here.

## Phase 3 · Strike suggestions

Issues #23-#27. Training windows, training notebook, inference, review mode, and
an end-to-end run.

**Gate 3 pass:** a full fight tagged with suggestions turned on, from video to
stat cards, with the time taken recorded and compared with manual tagging.

## Phase 4 · Validate and ship v1

Issues #28-#32. Evaluation, deployment on free tiers, user guide, case study,
v1.0.0 release.

**Gate 4 pass:** Freefly's team tags a fight on their own with the deployed tool.

## Research (no milestone)

Issues #33-#35. Automatic landed detection, target classification, and round
detection from the broadcast clock. Picked up only when the gates are on track.

## Risks

| Risk | Effect | Plan |
|---|---|---|
| Freefly does not reply | No Gate 1 comparison | Compare against their published figures; keep the pitch open |
| Footage rights unclear | Cannot share demos | Show demos privately; ask Byon early |
| Tracking swaps fighter IDs often | Bad suggestions | Manual ID fix in the tagger; colour heuristics |
| Not enough confirmed tags to train | Weak model | Tag more fights in Phase 1; use public clips |
| Coursework load | Slipped dates | Buffer weeks; cut research issues first |

## Project board

The GitHub Project "StrikeLens Roadmap" holds every issue with Status, Phase,
dates, and Size. The link is added here once the board exists.
