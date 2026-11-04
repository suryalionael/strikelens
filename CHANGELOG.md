# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Tagger video player: open a local file (never uploaded), `Space` to play and
  pause, 0.25x-2x speed, `←` / `→` frame stepping at a chosen frame rate, and a
  `mm:ss.mmm` clock. Other components read player state with `usePlayer()` (#6).
- API CRUD for fighters, fights, and tags on SQLite. Tags are validated with the
  shared schema rules, can be filtered by status and source, and CV suggestions
  can be created in bulk. Database path and CORS origins are configurable (#12).
- Tagger fight setup: create a fight with new or existing fighters, or open a
  saved one. Mark round start and end at the player time, edit times by typing,
  and save valid rounds through the API. The API rejects rounds that end before
  they start, overlap, or outnumber the scheduled rounds (#7).

## [0.0.1] - 2026-11-03

Foundation release. No product features yet.

### Added

- Repo structure, AGPL-3.0 licence, Code of Conduct, contributing guide, and
  security policy.
- Tagger skeleton (React, Vite, TypeScript strict, Tailwind) with a placeholder
  page and one Vitest test.
- API skeleton (FastAPI) with `GET /health`.
- Pure stat functions `accuracy`, `strikes_per_minute`, and `attempts_by_round`,
  tested against Freefly Metrics' published figures.
- CV package skeleton with a `strikelens-cv --version` CLI. Heavy CV dependencies
  are optional extras.
- Shared JSON Schemas for tags, fights, and fighters, validated in API tests.
- GitHub Actions CI with tagger, API, and CV jobs.
- Pre-commit hooks: Ruff, Prettier, file hygiene, and a 5 MB file size limit.
- Issue forms, PR template, and CODEOWNERS.
- Docs: vision, architecture, tag schema and hotkeys, stat definitions with open
  questions for Freefly, data policy, roadmap, dev setup, Claude Code workflow,
  and Freefly collaboration notes.
- ADRs 0001-0004: monorepo, AGPL licence, human in the loop, MediaPipe for pose.
- Labels, milestones, 35 issues, and the StrikeLens Roadmap project board.

[Unreleased]: https://github.com/suryalionael/strikelens/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/suryalionael/strikelens/releases/tag/v0.0.1
