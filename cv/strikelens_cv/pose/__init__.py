"""pose stage: keypoints for the red and the blue fighter in every frame.

The tracker's boxes (tracks.json) are cropped with a margin, and a pose backend
finds one person in each crop. v1 uses MediaPipe's 33 landmarks
(mediapipe_backend.py, needs the `pose` extra); RTMPose can replace it behind the
same interface (backend.py, ADR 0004). The rest is pure (core.py).

Output for one fight, under data/processed/<fight>/keypoints/:

- red.json, blue.json   the keypoint format, the landmark names, the fighter ID,
                        and per frame the box and [x, y, z, visibility] for each
                        landmark in image pixels, or null with a reason
"""

from strikelens_cv.pose.backend import PoseBackend
from strikelens_cv.pose.config import DEFAULT_POSE_CONFIG, PoseConfig, load_pose_config
from strikelens_cv.pose.core import (
    MEDIAPIPE_LANDMARKS,
    MEDIAPIPE_POSE_33,
    count_missing,
    crop_box,
    frame_pose,
    to_image,
)
from strikelens_cv.pose.run import PoseResult, model_path, pose

__all__ = [
    "DEFAULT_POSE_CONFIG",
    "MEDIAPIPE_LANDMARKS",
    "MEDIAPIPE_POSE_33",
    "PoseBackend",
    "PoseConfig",
    "PoseResult",
    "count_missing",
    "crop_box",
    "frame_pose",
    "load_pose_config",
    "model_path",
    "pose",
    "to_image",
]
