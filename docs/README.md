# Docs

Everything about StrikeLens that is not code. Start with `vision.md`, then
`architecture.md`.

## Product

| Doc | What it covers |
|---|---|
| [vision.md](vision.md) | Problem, users, pitch, v1 scope, non-goals |
| [roadmap.md](roadmap.md) | Phases, gates, dates, risks |
| [freefly-collab.md](freefly-collab.md) | Pitch summary, open questions, contact log, meeting notes |

## Design

| Doc | What it covers |
|---|---|
| [architecture.md](architecture.md) | Components, data flow, tag lifecycle, training loop |
| [rules.md](rules.md) | The UCC Kickstriking rules Byon fights under, and what they mean for StrikeLens |
| [tag-schema.md](tag-schema.md) | Strike taxonomy, tag fields, default hotkeys |
| [stat-definitions.md](stat-definitions.md) | Every stat formula, edge cases, open questions for Freefly |
| [data-policy.md](data-policy.md) | Who owns what, what never goes in git |

## Working on the code

| Doc | What it covers |
|---|---|
| [dev-setup.md](dev-setup.md) | Running and testing every part locally |
| [working-with-claude-code.md](working-with-claude-code.md) | The one-issue-at-a-time feature loop |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Branches, commits, PRs |

## Decisions

Architecture decision records (ADRs). Copy the template for a new one and take the
next number.

| ADR | Decision |
|---|---|
| [0000](decisions/0000-template.md) | Template |
| [0001](decisions/0001-monorepo.md) | One repo for tagger, API, CV, and schemas |
| [0002](decisions/0002-agpl-licence.md) | AGPL-3.0 licence |
| [0003](decisions/0003-human-in-the-loop.md) | Human in the loop for every counted strike |
| [0004](decisions/0004-pose-library.md) | MediaPipe for pose in v1, RTMPose as the upgrade path |
| [0005](decisions/0005-fighter-hotkeys.md) | Fighter hotkeys: `Q` for red, `W` for blue |
| [0006](decisions/0006-track-colour-calibration.md) | Kit and referee colour thresholds calibrated on Byon footage |
| [0007](decisions/0007-round-suggestions.md) | Round suggestions from scoreboard presence, not clock OCR |
