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
| `ingest.json` | The settings used and the video file name (never its path) |

Timestamps count from the start of the video file, the same clock as the tagger
and the tag schema's `timestamp_ms`. Settings are in `configs/ingest.toml` (frame
rate, JPEG quality, cut threshold, shortest shot). Pass `--config` to use another
file, and `--overwrite` to redo a fight's frames. Set `STRIKELENS_DATA_DIR` to
write somewhere other than `data/`.

`tests/test_ingest_end_to_end.py` runs the whole stage on a synthetic video it
generates itself. It skips unless FFmpeg and the `ingest` extra are installed, so
it does not run in CI.

Subpackages:

- `ingest/`: frame extraction (FFmpeg) and cut detection.
- `track/`: fighter detection and tracking, two stable IDs, referee filter.
- `pose/`: keypoints per fighter.
- `strikes/`: training windows, strike candidate model, inference to tags.
- `overlay/`: render boxes, skeletons, and a strike timeline onto video.

Data paths point into `data/` and `models/` at the repo root. Both are gitignored.
