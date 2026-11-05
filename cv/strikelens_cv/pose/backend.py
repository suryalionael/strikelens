"""The pose backend interface: a frame and a box in, keypoints out.

MediaPipe is the v1 backend (mediapipe_backend.py). RTMPose can replace it by
implementing the same protocol (ADR 0004). Keypoint files record the backend's
`format`, so keypoints from two backends are never mixed by mistake.
"""

from collections.abc import Sequence
from typing import Any, Protocol

from strikelens_cv.pose.core import Keypoint


class PoseBackend(Protocol):
    format: str
    landmark_names: Sequence[str]

    def estimate(self, image: Any, box: Sequence[float]) -> list[Keypoint] | None:
        """Keypoints for the one person in `box` of `image` (BGR, as OpenCV reads
        it), in image pixels. None when no pose is found."""
        ...

    def close(self) -> None: ...
