# StrikeLens CV pipeline

Python package `strikelens_cv`. Turns fight video into tracks, keypoints, and
strike suggestions in the shared tag schema.

```bash
uv sync
uv run strikelens-cv --version
uv run ruff check .
uv run pytest
```

Heavy dependencies are optional extras and are not installed by default:

| Extra | Installs | Used by |
|---|---|---|
| `ingest` | OpenCV, PySceneDetect | `ingest/` |
| `detect` | Ultralytics YOLO (+ ByteTrack) | `track/` |
| `pose` | MediaPipe | `pose/` (v1 default, see ADR 0004) |
| `train` | PyTorch | `strikes/` |

Install one with `uv sync --extra ingest`.

RTMPose (the pose upgrade path) is not an extra. MMPose installs with OpenMMLab's
`mim` tool (`uv pip install openmim && mim install mmpose`), and one of its
dependencies cannot be built by uv. Do this only when ADR 0004 is revisited.

## Ingest

Needs FFmpeg on your PATH and the `ingest` extra.

```bash
uv sync --extra ingest
uv run strikelens-cv ingest data/raw/fight.mp4 --fight "Byon 40 main event"
```

Writes to `data/processed/<fight>/` (gitignored):

| File | Contents |
|---|---|
| `frames/000000.jpg` ... | One JPEG per 1/fps seconds. Frame N is at N × 1000 / fps ms |
| `frames.json` | Every frame with its file name and `timestamp_ms` |
| `cuts.json` | Shots between camera cuts, each with `start_ms` and `end_ms` |
| `segment-suggestions.json` | Likely replays: runs of short shots in the cut list |
| `ingest.json` | The settings used and the video file name (never its path) |

Timestamps count from the start of the video file, the same clock as the tagger
and the tag schema's `timestamp_ms`. Settings are in `configs/ingest.toml` (frame
rate, JPEG quality, cut threshold, shortest shot). Pass `--config` to use another
file, and `--overwrite` to redo a fight's frames. Set `STRIKELENS_DATA_DIR` to
write somewhere other than `data/`.

## Replays and non-fight segments

Ingest also writes `segment-suggestions.json`. A run of at least `min_run` shots in
a row, each shorter than `short_shot_ms`, is suggested as a likely replay, because
live coverage holds a wide shot for a long time and replays cut quickly between
angles. Settings are in `configs/segments.toml`. To try other settings without
redoing frames:

```bash
uv run strikelens-cv suggest --fight "Byon 40 main event" --config configs/segments.toml
```

In the tagger, pick the file under "Load suggestions" and accept or dismiss each
one. Accepted and hand-marked segments are saved on the fight. Slow-motion
detection is not done yet.

Stages after ingest skip marked segments. Save the fight from the API next to the
other output, then filter frames with `strikelens_cv.segments`:

```bash
curl -s http://localhost:8000/fights/<fight-id> > data/processed/<fight>/fight.json
```

```python
from strikelens_cv.segments import frames_outside, load_segments

segments = load_segments(out_dir / "fight.json")
frames = frames_outside(manifest["frames"], segments)
```

`tests/test_ingest_end_to_end.py` runs the whole stage on a synthetic video it
generates itself. It skips unless FFmpeg and the `ingest` extra are installed, so
it does not run in CI.

## Track

Finds the two fighters in every frame and keeps them red and blue. Needs the
`ingest` and `detect` extras, ingest output for the fight, and YOLO weights in
`models/`:

```bash
uv sync --extra ingest --extra detect
uv run strikelens-cv track --fight "Byon 40 main event"
```

**Weights** are never committed and never downloaded automatically. Download
`yolo11n.pt` from the [Ultralytics assets
releases](https://github.com/ultralytics/assets/releases) and save it as
`models/yolo11n.pt`. To use another model, set `weights` in `configs/track.toml`.
Ultralytics is AGPL-3.0, which is why StrikeLens is too (ADR 0002).

How it works:

1. YOLO finds people in each frame and ByteTrack links them, shot by shot. The
   tracker starts again at every camera cut from `cuts.json`. Only frames inside
   the rounds marked in the tagger are tracked, and frames inside marked segments
   are skipped. To use them, save the fight from the API as `fight.json` first
   (see Replays above). Without rounds, the whole video is tracked, walkouts and
   crowd shots included, and the command warns about it. After changing the
   rounds, run `track` again; `assign` alone is not enough.
2. Tracks that look like the referee are dropped (see Referee filter). In each
   shot, the two strongest remaining tracks are the fighters. A track that never
   overlaps a fighter in time is treated as the same fighter under a new ID. A
   third person overlapping both is dropped.
3. Across shots, fighters are matched to red and blue. A fighter in clearly red
   or blue kit takes that corner (see Kit colour). Everyone else is matched by
   the colour of their shorts: a hue and saturation histogram of the middle of
   the box.

Writes to `data/processed/<fight>/` (gitignored):

| File | Contents |
|---|---|
| `detections.json` | Every person box with its shot, ByteTrack ID, confidence, and colour feature |
| `tracks.json` | Per frame, the red and blue box (or null). Per shot, which track IDs were red, blue, or dropped, and whether the match was uncertain. The rounds tracking was limited to (empty for the whole video) |

**Which fighter is red** cannot be known from the boxes alone. In Tryout fights
the kit says it (`"seeded_by": "kit"`). Otherwise, without corrections, the
fighter on the left in the first shot with two fighters is taken as red.
`tracks.json` says so (`"seeded_by": "left_is_red"`) and the command prints a
warning. Check that guess and correct it.

### Kit colour

In Tryout fights the red corner wears a red singlet and the blue corner a blue
one. For each box, `track` stores `torso_red` and `torso_blue` in
`detections.json`: the shares of the chest (the same pixels as the referee
filter) that are red or blue kit. A kit pixel is not skin, not dark, and has a
saturation of at least `kit_min_saturation` (0.4). Red is a hue of 0-15 or
320-360 degrees (Byon's red singlets measure about 336), blue 190-250.

In each shot, a fighter whose red share is at least `min_kit_share` (0.25) above
their blue share is red, and the other way round for blue. The kit comes after
corrections and before the shorts colour. It also teaches the shorts colours, so
shots where the kit is hard to see still match well. If two fighters in a shot
claim the same corner, or a correction already holds it, the kit is ignored for
that shot. Shirtless fighters show skin and the referee wears black, so neither
has kit, and those fights work as before. `tracks.json` marks each shot the kit
decided (`"by_kit": true`), and the command prints how many there were.

Known limits. Check these on real footage:

- **Gloves in the chest band.** With a high guard, red or blue gloves can cover
  the chest. If the gloves are not in the corner colour, this can mislead the kit.
- **Blue canvas or ropes** between the arms count as blue.
- **Events where the kit does not match the corner.** Set `kit_corner = false`.

### Referee filter

For each box, `track` samples the chest (20-45% down the box, middle half across)
and stores two shares in `detections.json`: `torso_dark`, the share of dark
pixels, and `torso_skin`, the share of skin pixels. `referee_rule` picks which one
finds the referee:

- **`dark` (default).** Byon referees wear black. A track whose average
  `torso_dark` is at least `min_torso_dark` (0.5) is dropped as the referee. This
  works for shirtless fighters (Madness) and for fighters in red and blue
  singlets (Tryouts). A pixel is dark when its brightest channel is at most
  `dark_max_value` (100) and it is not skin. The brightest channel is used instead
  of brightness (Y), because a pure blue singlet has a Y of about 29 and would
  pass as black. The skin check keeps very dark skin in shadow from passing as a
  black shirt.
- **`skin`.** For shirtless fighters and a referee in a shirt that is not black.
  A track whose average `torso_skin` is below `min_torso_skin` (0.25) is dropped.
  Fighters in a top are dropped too: on the first Tryout run, fighters in
  singlets were dropped from most frames.

Skin is found with the usual YCrCb rule. Each pixel's Cr and Cb must fall inside
`skin_cr` and `skin_cb`. Brightness is ignored, so one range covers light and dark
skin. All of these are in `configs/track.toml`. The chest is measured while
detecting, so after changing them run `track` again. Detections from before the
dark rule have no `torso_dark`, and the dark rule keeps all of their tracks.

The kit and dark thresholds were calibrated on labelled boxes from a Tryout and a
Madness fight. See [ADR 0006](../docs/decisions/0006-track-colour-calibration.md)
for the measurements, and repeat them when a new event looks different.

Known limits. Check these on real footage before trusting the filter:

- **A referee not in black** (white or grey shirt) is not dark. Use the skin rule
  if the fighters are shirtless, or remove the referee with corrections.
- **Fighters in black or very dark kit** look like the referee under the dark
  rule. Pin them with corrections, or set `referee_filter = false`.
- **Fighters in a top** (a sports top or a rash guard) look like the referee under
  the skin rule. Use the dark rule, set `referee_filter = false`, or pin the
  fighters with corrections. A correction always beats the filter.
- **Skin-coloured things count as skin**: a beige or brown shirt, a warm
  background, or a face. In close-ups the chest band can catch the face. On
  Ultralytics' sample photo of two men in suits, the band measured 40% and 56% skin,
  so neither would be removed. Wide ring shots frame people full-length, which
  should help, but this is not measured yet.

To measure the filter, correct some tracks (referee as `none`, fighters as `red` or
`blue`), then:

```bash
uv run strikelens-cv referee --fight "Byon 40 main event" --corrections track-corrections.json
```

It prints the share of referee tracks removed and the share of fighter tracks
wrongly removed.

### Corrections

`track-corrections.json` fixes the assignment by hand. The tagger will write this
file later. For now, write it yourself from the shot and track IDs in
`tracks.json`:

```json
{"corrections": [
  {"shot": 0, "track_id": 2, "corner": "red"},
  {"shot": 4, "track_id": 7, "corner": "none"}
]}
```

`corner` is `red`, `blue`, or `none`. `none` removes a track, for example the
referee. A correction also teaches the colour references, so fixing one shot
helps the shots after it. To redo the assignment without detecting again:

```bash
uv run strikelens-cv assign --fight "Byon 40 main event" --corrections track-corrections.json
```

### Counting swaps

A swap is a stretch of frames where red and blue are the wrong way round. To
measure it, correct every shot of a stretch, then compare that with the automatic
assignment:

```bash
uv run strikelens-cv swaps --fight "Byon 40 main event" --corrections track-corrections.json
```

Settings are in `configs/track.toml`. `tests/test_track_end_to_end.py` runs YOLO
on a synthetic clip. It skips unless the extras and the weights are installed.

## Pose

Pose finds keypoints for the red and the blue fighter in every frame. It needs
the ingest and pose extras, and the MediaPipe model in `models/`:

```bash
uv sync --extra ingest --extra detect --extra pose
uv run strikelens-cv pose --fight "Byon 40 main event"
```

Get `pose_landmarker_full.task` from the [MediaPipe Pose Landmarker
models](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker#models)
and save it in `models/`. It is never downloaded automatically.

Each fighter box from `tracks.json` is padded by 10% (`box_margin`) so fists and
feet are not cut off, then MediaPipe looks for one person in the crop. Output goes
to `data/processed/<fight>/keypoints/red.json` and `blue.json`:

- `format`: `mediapipe_pose_33`, and `landmarks`: the 33 names in order. Training
  windows must keep this, so keypoints from another backend are never mixed in.
- `fighter_id`: from `fight.json` when it is there (see Replays above), else null.
- `frames`: per frame, the `index`, `timestamp_ms`, `box`, and `keypoints`: one
  `[x, y, z, visibility]` per landmark. `x` and `y` are image pixels. `z` is
  MediaPipe's depth, scaled by the crop width, so only its relative size means
  anything.
- A frame without keypoints has `keypoints: null` and a `missing` reason, never
  zeros: `skipped` (outside the marked rounds, or inside a replay or non-fight
  segment), `no_box` (tracking found
  no fighter), or `no_pose` (MediaPipe found nobody, or was below
  `min_pose_confidence`).

The command prints how many frames have keypoints and how many are missing, per
corner. Settings are in `configs/pose.toml`.

Known limit: a person cut off by the frame edge often gets no pose. On a sample
photo, MediaPipe found 33 and 32 visible keypoints for the two people in full
view, and nothing for the two cut off at the edges. How it does on clinches, fast
kicks, and motion blur is unmeasured until a practice clip (#3) and the overlay
video (#22).

The backend sits behind a small interface (`pose/backend.py`: an image and a box
in, keypoints out), so RTMPose can replace MediaPipe (ADR 0004).
`tests/test_pose_end_to_end.py` runs MediaPipe on a sample photo. It skips unless
the pose extra and the model are installed.

## Overlay

Draws the red and blue boxes, their skeletons, and a strike timeline onto the
fight, for the Gate 2 demo video. Needs FFmpeg, the `ingest` extra, and the
output of `ingest`, `track`, and `pose` for the fight:

```bash
uv run strikelens-cv overlay --fight "Byon 40 main event" --round 1
```

It renders the frames ingest extracted, at the ingest fps (10 by default), so
every box sits on the frame it was measured on. For a smoother demo, ingest that
fight at a higher `fps` in `configs/ingest.toml` and run the stages again.

What it reads from `data/processed/<fight>/`:

- `frames.json`, `frames/`, `detections.json`, `tracks.json`: required.
- `keypoints/red.json`, `keypoints/blue.json`: skeletons. Without them, boxes only.
- `fight.json`: rounds (see Replays above). `--round N` renders one round.
  Without `--round`, every round. Without rounds, every frame that was tracked.
- `tags.json`: tags for the timeline. Save them from the API like `fight.json`:

  ```bash
  curl -s "http://localhost:8000/fights/<fight-id>/tags?status=confirmed" > data/processed/<fight>/tags.json
  ```

  Only confirmed tags are drawn: a tick above the line for red, below for blue.
  Without the file, the timeline is empty.

It writes `overlay.mp4` (or `overlay-round-<N>.mp4`): H.264, which plays in
browsers and on phones. Every frame carries the `credit` line from
`configs/overlay.toml`.

**Writing corrections.** `--ids` draws every person instead, labelled with shot
and track ID (`s3 t12`), in red or blue when the track was assigned to a corner
and grey otherwise. Use it to write `track-corrections.json` (see Corrections).
It writes `overlay-ids.mp4` or `overlay-ids-round-<N>.mp4`.

**Before sharing.** The video uses real footage. Read the Demo material section of
[docs/data-policy.md](../docs/data-policy.md) before it leaves the team.

`tests/test_overlay_end_to_end.py` renders synthetic frames and checks the MP4
with ffprobe. It skips unless FFmpeg and the `ingest` extra are installed.

Subpackages:

- `ingest/`: frame extraction (FFmpeg) and cut detection.
- `segments/`: replay suggestions from the cut list, and skipping marked segments.
- `track/`: fighter detection and tracking, two stable IDs, corrections, swap count.
- `pose/`: keypoints per fighter per frame, behind a swappable backend.
- `strikes/`: training windows, strike candidate model, inference to tags.
- `overlay/`: render boxes, skeletons, and a strike timeline onto video.

Data paths point into `data/` and `models/` at the repo root. Both are gitignored.
