"""Pure pose helpers: crops, coordinates, and the per-frame keypoint records.

No MediaPipe here, so CI tests all of it. The backend (backend.py) does the
model call; this module decides what gets written.
"""

from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict

Box = list[float]  # [x1, y1, x2, y2] in pixels
Keypoint = list[float]  # [x, y, z, visibility]; x, y, z in image pixels
Corner = Literal["red", "blue"]
Missing = Literal["skipped", "no_box", "no_pose"]

CORNERS: tuple[Corner, ...] = ("red", "blue")

MEDIAPIPE_POSE_33 = "mediapipe_pose_33"
MEDIAPIPE_LANDMARKS = (
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
)


class FramePose(TypedDict):
    index: int
    timestamp_ms: int
    box: Box | None
    keypoints: list[Keypoint] | None
    missing: Missing | None


def crop_box(box: Sequence[float], width: int, height: int, margin: float) -> Box | None:
    """The box padded by `margin` of its size on each side, in whole pixels, inside
    the image. None when nothing of it is inside the image."""
    w, h = box[2] - box[0], box[3] - box[1]
    x1 = max(0, round(box[0] - w * margin))
    y1 = max(0, round(box[1] - h * margin))
    x2 = min(width, round(box[2] + w * margin))
    y2 = min(height, round(box[3] + h * margin))
    if x2 <= x1 or y2 <= y1:
        return None
    return [float(x1), float(y1), float(x2), float(y2)]


def to_image(landmarks: Sequence[Sequence[float]], crop: Sequence[float]) -> list[Keypoint]:
    """Landmarks as 0-1 shares of the crop (x, y, z, visibility) into image pixels.

    MediaPipe's z is depth on roughly the same scale as x, so it is scaled by the
    crop width. Values are rounded to keep the files small.
    """
    w, h = crop[2] - crop[0], crop[3] - crop[1]
    return [
        [
            round(crop[0] + x * w, 1),
            round(crop[1] + y * h, 1),
            round(z * w, 1),
            round(visibility, 3),
        ]
        for x, y, z, visibility in landmarks
    ]


def frame_pose(
    index: int,
    timestamp_ms: int,
    skipped: bool,
    box: Box | None,
    keypoints: list[Keypoint] | None,
) -> FramePose:
    """One frame's record. Missing keypoints are null with a reason, never zeros."""
    missing: Missing | None = None
    if skipped:
        missing, keypoints = "skipped", None
    elif box is None:
        missing, keypoints = "no_box", None
    elif keypoints is None:
        missing = "no_pose"
    return {
        "index": index,
        "timestamp_ms": timestamp_ms,
        "box": box,
        "keypoints": keypoints,
        "missing": missing,
    }


def count_missing(frames: Sequence[FramePose]) -> Mapping[str, int]:
    """How many frames have keypoints, and how many are missing for each reason."""
    counts = {"found": 0, "skipped": 0, "no_box": 0, "no_pose": 0}
    for f in frames:
        counts[f["missing"] or "found"] += 1
    return counts
