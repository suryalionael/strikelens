# 0004. MediaPipe for pose in v1, RTMPose as the upgrade path

- **Status:** accepted
- **Date:** 2026-11-03

## Context

The strike model reads keypoint sequences, so we need a pose estimator that runs
on each fighter box. Two realistic free options:

| | MediaPipe Pose | RTMPose (MMPose) |
|---|---|---|
| Licence | Apache-2.0 | Apache-2.0 |
| Install | `pip install mediapipe` | OpenMMLab stack: PyTorch, MMCV, MMEngine, installed with `mim` |
| Runs on | CPU, fast; works on a laptop | GPU recommended for good speed |
| People per call | Can detect several, most reliable on one person per crop | Top-down, many people with a detector |
| Keypoints | 33 body landmarks | 17 (COCO) or 133 (whole body) |
| Accuracy on fast, occluded motion | Lower; struggles with overlap and motion blur | Higher on benchmarks |
| Fit with our pipeline | We already crop each fighter from YOLO boxes | Same, and can use our boxes |

The CV phases are short (two weeks for the baseline), compute is free-tier Colab or
Kaggle, and the author works part time. MMPose also failed to install with uv in
our setup (its dependency `chumpy` does not build), so it would need a separate
install path.

## Decision

Use **MediaPipe** for v1. Run it on each fighter's crop from the tracker. Keep the
pose stage behind a small interface (frames and boxes in, keypoints per fighter per
frame out) so the backend can change.

**RTMPose is the upgrade path** if MediaPipe keypoints are not good enough for the
strike model.

## Consequences

- Fast to set up and runs on any laptop, so Phase 2 can start without a GPU.
- Keypoint format is MediaPipe's 33 landmarks. Training windows must record which
  format they use, so a later switch does not silently mix formats.
- Accuracy on clinches, overlap, and fast kicks may be poor. We will see this in the
  Gate 2 overlay video and in strike model results.
- **Revisit when:** keypoints drop out or jitter on more than a small share of strike
  moments in the Gate 2 review, or the strike model's recall is limited by pose
  quality (issue #28). Switching means adding an RTMPose backend, re-extracting
  keypoints, and retraining.
- RTMPose is not a `pyproject.toml` extra. Install notes are in `cv/README.md`.
