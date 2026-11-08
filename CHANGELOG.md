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
- Tagger hotkey tagging: `Q`/`W` pick the fighter, then weapon, outcome, and
  target keys save a confirmed human tag at the time of the first key, in the
  round found from the round marks. Keys work in any order and `Esc` clears the
  draft. Fighter keys are recorded in ADR 0005 (#8).
- Tagger tag panel: every fighter, weapon, outcome, and target option is a button
  that does the same as its hotkey, corners are labelled in words as well as
  colour, and the last saved tag is confirmed for three seconds (#9).
- API stats engine and `GET /fights/{id}/stats`: round and fight time, attempts,
  landed, accuracy, and strikes per minute per fighter and per round, weapon mix
  per weapon and group, and target distribution. Only confirmed tags inside their
  round count, undefined values are null, partial rounds are flagged, and the
  response lists the provisional rules in use (#13).
- Tagger stat cards: a headline card per fighter and red/blue bar charts for
  attempts per round, weapon mix, and target distribution, each with a table
  view. Undefined values show as a dash, partial rounds and uncounted tags are
  flagged, provisional rules are listed, and stats refresh after each tag (#14).
- Tagger timeline: red and blue lanes over the marked rounds, with round bands, a
  playhead, and outcome shown by marker shape. Clicking a marker or the track
  seeks the video. Stays smooth with hundreds of tags (#10).
- Tagger edit and undo: pick a tag from the list or timeline to change its
  fighter, weapon, outcome, target, or time (a new time moves it to the right
  round), or delete it after confirming. `Ctrl+Z` / `Cmd+Z` undoes the last new
  tag, edit, or delete, up to 50 steps, through the API (#11).
- Tagger export: four 1080x1350 PNG stat cards for an Instagram carousel, each
  with the fighters, an editable credit line, and a provisional-definitions note;
  a CSV of confirmed tags in tag schema columns; and a long-format stats CSV (#15).
- CV ingest: `strikelens-cv ingest` extracts frames with FFmpeg at the rate in
  `cv/configs/ingest.toml`, each mapped to video ms, and writes the shots between
  camera cuts found by PySceneDetect to `data/processed/<fight>/` (#17).
- Replay and non-fight segments: mark them in the tagger, or accept likely replays
  that `strikelens-cv` suggests from runs of short shots. Tags inside a segment are
  flagged and not counted (`segment_tags` in the stats). Segments do not shorten
  round time. Both rules are provisional (open question 12). Later CV stages can
  skip segments with `frames_outside` (#18).
- CV tracking: `strikelens-cv track` finds people with YOLO and ByteTrack shot by
  shot, keeps two fighters per shot, and matches them to red and blue across cuts
  by the colour of their shorts. `assign` redoes the matching with a corrections
  file, and `swaps` counts red and blue swaps against it. Weights are read from
  `models/` and never downloaded. Red is guessed as the left fighter until
  corrected (#19).
- Referee filter: tracking drops a person whose chest is mostly not skin, since
  kickboxers fight shirtless and the referee wears a shirt. Thresholds live in
  `cv/configs/track.toml`, the filter can be switched off per fight, and a
  correction always wins. `strikelens-cv referee` reports how many referee tracks
  were removed and how many fighter tracks were removed by mistake (#20).
- Pose keypoints: `strikelens-cv pose` runs MediaPipe on each fighter box from
  tracking and writes 33 keypoints per frame to `keypoints/red.json` and
  `blue.json`, with the format recorded. Frames without keypoints are null with a
  reason (skipped, no box, no pose), never zeros. The backend can be swapped for
  RTMPose. The model is read from `models/` and never downloaded (#21).
- Kit colour corners: in Tryout fights, where the red corner wears a red singlet
  and the blue corner a blue one, tracking reads red and blue from the kit on the
  chest. Fights without corner kit work as before. Turn it off with
  `kit_corner = false` (#19).
- Referee filter by a dark shirt: Byon referees wear black, so the default rule
  now drops a person whose chest is mostly dark. It works for shirtless fighters
  and for fighters in singlets, which the skin rule dropped. The skin rule is
  still there (`referee_rule = "skin"`) (#20).
- Tracking only inside marked rounds: frames outside the rounds in `fight.json`
  (walkouts, intros, breaks, the result) are skipped. A fight with no rounds is
  still tracked over the whole video, with a warning (#19).
- Overlay video: `strikelens-cv overlay` draws the red and blue boxes, skeletons,
  and a strike timeline from confirmed tags onto the fight, one round or all.
  `--ids` labels every person with shot and track ID, to help write corrections.
  Output stays in `data/processed/` (#22).
- Fight rules: `docs/rules.md` summarises the UCC Kickstriking rules Byon fights
  under. Open questions 13 and 14 were added for Freefly (#54).
- Video navigation: a seek bar over the whole video with the time under the
  pointer, a Go to field (`m:ss` or `h:mm:ss`), and jump keys: Shift+arrows for
  5 s and Alt+arrows for 30 s (#60).
- Round suggestions: ingest finds when the broadcast scoreboard is on screen and
  writes `round-suggestions.json`. The tagger lists the rounds to check and uses
  them in one click. Rounds that end early are marked to check (ADR 0007) (#35).
- Review mode for CV suggestions: Tab and Shift+Tab jump between pending suggestions,
  the usual keys change the current one, Enter confirms, X rejects, and Ctrl+Z
  undoes. With progress and a confidence filter. Confirmed suggestions keep
  `source: cv` (#26).
- Training windows: `strikelens-cv windows` cuts keypoint windows around confirmed
  tags, rejected suggestions, and times with no strike, split by whole fight
  (ADR 0008) (#23).
- Strike suggestions: `strikelens-cv suggest-strikes` turns peaks in a model's score
  into pending CV tags, and `--post` adds them to the API for review. The model for
  now is an uncalibrated motion baseline with no weapon guess (ADR 0009) (#25).

### Changed

- The stats panel loads on demand, so the tagger's first download drops from 678 kB
  to 280 kB (#70).

### Fixed

- A fast second `Ctrl+Z` / `Cmd+Z` could undo the same step twice (#47).
- A round mark changed while its save was still in flight could be left unsaved,
  and a round save could undo a segment save made just before it (#18).
- Tracking boxed the referee as a fighter and missed the red kit on Byon footage.
  The kit and referee colour thresholds are now calibrated on labelled boxes from
  a Tryout and a Madness fight (ADR 0006): red kit from 320 degrees,
  `dark_max_value` 100, `min_kit_share` 0.25 (#19, #20).
- In long camera shots, tracking could drop a fighter, swap red and blue, or box a
  spectator. Tracks now join a corner by their own kit, and tracks much smaller
  than the biggest person in the shot are dropped (`min_fighter_area`) (#19).
- A track ID that ByteTrack passed from one person to another put a corner's box on
  the wrong person. Tracks are now cut where the kit, the dark share, or the box
  position jumps (#64).

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
