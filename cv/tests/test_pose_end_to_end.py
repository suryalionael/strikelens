"""Run MediaPipe for real on a sample photo.

Skips unless the pose extra and models/<model> are installed, so it never runs in
CI. The photo is bus.jpg, a sample that ships inside the ultralytics package
(detect extra), so no footage is involved.
"""

from pathlib import Path

import pytest

from strikelens_cv.paths import REPO_ROOT
from strikelens_cv.pose import MEDIAPIPE_POSE_33, PoseConfig

pytest.importorskip("mediapipe")
cv2 = pytest.importorskip("cv2")
assets = pytest.importorskip("ultralytics.utils").ASSETS
MODEL = REPO_ROOT / "models" / PoseConfig().model
if not MODEL.is_file():
    pytest.skip("needs the pose model in models/", allow_module_level=True)

# A person in bus.jpg (810 x 1080), standing on the left, found by yolo11n.
PERSON = [47.0, 400.0, 239.0, 904.0]


def test_mediapipe_finds_33_keypoints_in_the_box() -> None:
    from strikelens_cv.pose.mediapipe_backend import MediaPipeBackend

    image = cv2.imread(str(Path(assets) / "bus.jpg"))
    backend = MediaPipeBackend(MODEL, PoseConfig())
    try:
        keypoints = backend.estimate(image, PERSON)
    finally:
        backend.close()
    assert backend.format == MEDIAPIPE_POSE_33
    assert keypoints is not None
    assert len(keypoints) == 33
    crop = [28.0, 350.0, 258.0, 954.0]  # the box with the 10% margin
    visible = [k for k in keypoints if k[3] > 0.5]
    assert len(visible) >= 20
    for x, y, _, _ in visible:
        assert crop[0] - 5 <= x <= crop[2] + 5
        assert crop[1] - 5 <= y <= crop[3] + 5
    nose, left_ankle = keypoints[0], keypoints[27]
    assert nose[1] < left_ankle[1]  # head above feet


def test_no_pose_in_an_empty_crop() -> None:
    from strikelens_cv.pose.mediapipe_backend import MediaPipeBackend

    image = cv2.imread(str(Path(assets) / "bus.jpg"))
    backend = MediaPipeBackend(MODEL, PoseConfig())
    try:
        # The sky above the bus: no person.
        assert backend.estimate(image, [600.0, 0.0, 800.0, 120.0]) is None
    finally:
        backend.close()
