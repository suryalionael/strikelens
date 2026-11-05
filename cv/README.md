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
2. In each shot, the two strongest tracks are the fighters. A track that never
   overlaps a fighter in time is treated as the same fighter under a new ID. A
   third person overlapping both is dropped. This is often the referee; the
   proper referee filter is #20.
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

Subpackages:

- `ingest/`: frame extraction (FFmpeg) and cut detection.
- `segments/`: replay suggestions from the cut list, and skipping marked segments.
- `track/`: fighter detection and tracking, two stable IDs, corrections, swap count.
- `pose/`: keypoints per fighter.
- `strikes/`: training windows, strike candidate model, inference to tags.
- `overlay/`: render boxes, skeletons, and a strike timeline onto video.

Data paths point into `data/` and `models/` at the repo root. Both are gitignored.
