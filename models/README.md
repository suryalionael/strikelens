# models/

Local-only model weights (`*.pt`, `*.onnx`, checkpoints). Everything here is
gitignored except this file.

The tracking stage expects `yolo11n.pt` here (set in `cv/configs/track.toml`).
Get it from the [Ultralytics assets
releases](https://github.com/ultralytics/assets/releases). It is never downloaded
automatically.

The pose stage expects `pose_landmarker_full.task` here (set in
`cv/configs/pose.toml`). Get it from the [MediaPipe Pose Landmarker
models](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker#models).
It is never downloaded automatically either.

Share weights through a private channel, never through git. See
[docs/data-policy.md](../docs/data-policy.md).
