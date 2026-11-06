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
   tracker starts again at every camera cut from `cuts.json`. Frames inside
   segments marked in the tagger are skipped. To use them, save the fight from the
   API as `fight.json` first (see Replays above).
2. Tracks that look like the referee are dropped (see Referee filter). In each
   shot, the two strongest remaining tracks are the fighters. A track that never
   overlaps a fighter in time is treated as the same fighter under a new ID. A
   third person overlapping both is dropped.
3. Across shots, fighters are matched to red and blue by the colour of their
   shorts: a hue and saturation histogram of the middle of the box.

Writes to `data/processed/<fight>/` (gitignored):

| File | Contents |
|---|---|
| `detections.json` | Every person box with its shot, ByteTrack ID, confidence, and colour feature |
| `tracks.json` | Per frame, the red and blue box (or null). Per shot, which track IDs were red, blue, or dropped, and whether the match was uncertain |

**Which fighter is red** cannot be known from the boxes alone. Without
corrections, the fighter on the left in the first shot with two fighters is taken
as red. `tracks.json` says so (`"seeded_by": "left_is_red"`) and the command
prints a warning. Check that guess and correct it.

### Referee filter

For each box, `track` samples the chest (20-45% down the box, middle half across)
and stores two shares in `detections.json`: `torso_dark`, the share of dark
pixels, and `torso_skin`, the share of skin pixels. `referee_rule` picks which one
finds the referee:

- **`dark` (default).** Byon referees wear black. A track whose average
  `torso_dark` is at least `min_torso_dark` (0.5) is dropped as the referee. This
  works for shirtless fighters (Madness) and for fighters in red and blue
  singlets (Tryouts). A pixel is dark when its brightest channel is at most
  `dark_max_value` (70) and it is not skin. The brightest channel is used instead
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
  zeros: `skipped` (inside a replay or non-fight segment), `no_box` (tracking found
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

Subpackages:

- `ingest/`: frame extraction (FFmpeg) and cut detection.
- `segments/`: replay suggestions from the cut list, and skipping marked segments.
- `track/`: fighter detection and tracking, two stable IDs, corrections, swap count.
- `pose/`: keypoints per fighter per frame, behind a swappable backend.
- `strikes/`: training windows, strike candidate model, inference to tags.
- `overlay/`: render boxes, skeletons, and a strike timeline onto video.

Data paths point into `data/` and `models/` at the repo root. Both are gitignored.
