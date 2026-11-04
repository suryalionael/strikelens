# Roadmap

Five phases, each ending in a gate. A gate is a demo or result that proves the
phase worked. GitHub milestones mirror this table.

Capacity: about 8-10 hours a week.

| Phase | Dates | Gate |
|---|---|---|
| Phase 0 · Setup | 2026-11-03 to 2026-11-08 | Repo, docs, CI green |
| Phase 1 · Tagging app MVP | 2026-11-09 to 2026-11-29 | **Gate 1:** one fight tagged and compared with Freefly's published numbers |
| Phase 2 · CV baseline | 2026-11-30 to 2026-12-13 | **Gate 2:** overlay demo video ready to share |
| Buffer: exams and winter break | 2026-12-14 to 2027-01-03 | No milestone |
| Phase 3 · Strike suggestions | 2027-01-04 to 2027-01-31 | **Gate 3:** assisted tagging works end to end on a full fight |
| Phase 4 · Validate and ship v1 | 2027-02-01 to 2027-02-21 | **Gate 4:** Freefly contacted, counting rules confirmed, v1 handed over |

## When we contact Freefly

We contact Freefly once the product works end to end, at the start of Phase 4.
Showing a finished tool is a stronger first message than a plan.

Until then:

- Code follows the provisional counting rules in
  [stat-definitions.md](stat-definitions.md). The open questions stay open.
- Gate 1 compares our count with the numbers Freefly has already published on
  Instagram, not with private data from them.
- The fighter hotkeys are decided by the owner before #8, not by Freefly.

## Phase 0 · Setup

Issues #1-#3. Repo, docs, CI, practice clips.

The Freefly DM (#4) and the stat definitions question (#5) moved to Phase 4. See
[When we contact Freefly](#when-we-contact-freefly).

## Phase 1 · Tagging app MVP

Issues #6-#16. Player, fight setup, hotkey tagging, timeline, edit and undo, API,
stats engine, stat cards, export, and the Gate 1 comparison.

Suggested order: #12 (API) and #6 (player) first, then #7, #8, #9, #10, #11, then
#13, #14, #15, and finally #16.

**Gate 1 pass:** one full fight tagged in StrikeLens, numbers compared with the
figures Freefly published for the same fight, and every gap explained (definition
difference or counting error). No demo to Freefly yet.

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

Issues #4, #5, #28-#32. First contact with Freefly, stat definitions, evaluation,
deployment on free tiers, user guide, case study, v1.0.0 release.

Send the DM (#4) on the first day of the phase, with a link to the working tool.
While waiting for a reply, work on evaluation (#28) and deployment (#29). When
Freefly answers, settle the open questions (#5) and update the stat functions
before the handover (#32).

**Gate 4 pass:** Freefly's team tags a fight on their own with the deployed tool.
If Freefly has not replied by the end of the phase, release v1.0.0 publicly and
keep the handover open.

## Research (no milestone)

Issues #33-#35. Automatic landed detection, target classification, and round
detection from the broadcast clock. Picked up only when the gates are on track.

## Risks

| Risk | Effect | Plan |
|---|---|---|
| Freefly does not reply | No handover in Phase 4 | Release v1 publicly; keep the pitch open |
| Freefly's counting rules differ from the provisional ones | Numbers change late, in Phase 4 | Rules live in pure, tested functions in one place, so a change is small |
| Freefly needs longer than three weeks to reply | Handover slips past Feb 21 | Handover can follow the v1.0.0 release |
| A fight with published Freefly numbers is hard to find | No Gate 1 comparison | Pick the Gate 1 fight early in Phase 1 |
| Footage rights unclear | Cannot share demos | Show demos privately; ask Byon early |
| Tracking swaps fighter IDs often | Bad suggestions | Manual ID fix in the tagger; colour heuristics |
| Not enough confirmed tags to train | Weak model | Tag more fights in Phase 1; use public clips |
| Coursework load | Slipped dates | Buffer weeks; cut research issues first |

## Project board

The GitHub Project **[StrikeLens Roadmap](https://github.com/users/suryalionael/projects/5)**
holds every issue.

| View | Use it for |
|---|---|
| [Kanban](https://github.com/users/suryalionael/projects/5/views/2) | Day-to-day work. Columns are the Status field |
| [Timeline](https://github.com/users/suryalionael/projects/5/views/3) | Phases over time, using Start date and Target date |
| [Table](https://github.com/users/suryalionael/projects/5/views/1) | Bulk edits of fields |

Fields:

| Field | Values |
|---|---|
| Status | Backlog, Ready, In progress, In review, Done |
| Phase | Phase 0 to Phase 4, Research |
| Start date, Target date | Planned dates inside the phase, dependencies first |
| Size | S (an evening), M (a few sessions), L (most of a week) |

Research issues have no dates. They get dates only when picked up.

Status flow follows the feature loop in
[working-with-claude-code.md](working-with-claude-code.md): Ready, In progress,
In review (PR open), Done (merged).
