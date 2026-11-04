# Vision

## Problem

Freefly Metrics (@freefly.combat) publishes kickboxing fight stats on Instagram.
They count strikes by hand. Hand counting means watching each fight slowly, often
more than once, so it takes a long time per fight. That limits how many fights
can be covered and how fast stats come out after an event. (How long it takes
Freefly today is one of our open questions.)

Fully automatic strike counting from broadcast video is not reliable yet. Fighters
overlap, the camera cuts, replays repeat moments, and "landed" is a judgement call.
A tool that guesses everything would produce numbers nobody can trust.

## Idea

Keep a person in charge of every number, and make that person much faster.

1. The analyst tags strikes with single-key hotkeys while the video plays.
2. A CV model watches the same video and flags moments where a strike probably
   happened. The analyst jumps between flags and confirms or rejects each one.
3. Stats are calculated automatically from confirmed tags.
4. Stat cards export straight to Instagram carousel size.

Every confirmed or rejected suggestion becomes training data, so the model should
need less correcting over time.

**Pitch:** Count a fight in a fraction of the time, with numbers you can still trust.

## Users

- **Primary: Freefly's analysts.** They know the sport and already count fights.
  They want speed and control, not a black box.
- **Secondary: Freefly's audience.** They see the stat cards. They care that the
  numbers are consistent and explained.
- **Later: other promotions and analysts** who want the same workflow.

## v1 scope

- Byon Combat kickboxing footage.
- Tagging app with hotkeys, timeline, edit, undo.
- Stats: attempts, landed, accuracy, strikes per minute, per-round splits, weapon
  mix, target distribution.
- CV baseline: fighter tracking, pose keypoints, overlay video.
- Strike suggestions the analyst reviews.
- PNG stat cards and CSV export.

## Non-goals for v1

- Fully automatic landed-strike detection or target classification.
- Live (real-time) analysis during broadcasts.
- Hosting, streaming, or redistributing footage.
- Other combat sports (MMA, boxing, Muay Thai scoring rules).
- Paid infrastructure. The project must stay free to run.
- Judging or predicting fight outcomes.

## What success looks like

- Gate 1: one fight tagged in StrikeLens matches the numbers Freefly published for
  it closely, and where it differs, we can explain why.
- Gate 3: assisted tagging of a full fight takes clearly less time than tagging the
  same fight by hand in StrikeLens. Freefly's own baseline is asked in Phase 4.
- Gate 4: Freefly's team uses v1 on real fights without help from the author.
