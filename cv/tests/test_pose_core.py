"""Pure pose helpers: crops, coordinates, missing frames, and the config."""

from pathlib import Path

import pytest

from strikelens_cv.pose import (
    MEDIAPIPE_LANDMARKS,
    PoseConfig,
    count_missing,
    crop_box,
    frame_pose,
    load_pose_config,
    to_image,
)
from strikelens_cv.pose.config import DEFAULT_POSE_CONFIG


def test_mediapipe_has_33_landmarks() -> None:
    assert len(MEDIAPIPE_LANDMARKS) == 33
    assert len(set(MEDIAPIPE_LANDMARKS)) == 33
    assert MEDIAPIPE_LANDMARKS[0] == "nose"
    assert MEDIAPIPE_LANDMARKS[32] == "right_foot_index"


def test_crop_box_adds_the_margin() -> None:
    assert crop_box([100, 100, 200, 300], 640, 480, 0.1) == [90.0, 80.0, 210.0, 320.0]


def test_crop_box_stays_inside_the_image() -> None:
    assert crop_box([-20, 10, 100, 470], 640, 480, 0.1) == [0.0, 0.0, 112.0, 480.0]


def test_crop_box_outside_the_image_is_none() -> None:
    assert crop_box([700, 10, 800, 100], 640, 480, 0.1) is None


def test_to_image_maps_crop_shares_to_pixels() -> None:
    keypoints = to_image([(0.0, 0.0, 0.0, 1.0), (0.5, 1.0, -0.1, 0.42)], [100, 50, 300, 450])
    assert keypoints == [[100.0, 50.0, 0.0, 1.0], [200.0, 450.0, -20.0, 0.42]]


def test_frame_with_keypoints() -> None:
    kp = [[1.0, 2.0, 0.0, 0.9]]
    assert frame_pose(3, 300, False, [0, 0, 10, 10], kp) == {
        "index": 3,
        "timestamp_ms": 300,
        "box": [0, 0, 10, 10],
        "keypoints": kp,
        "missing": None,
    }


@pytest.mark.parametrize(
    ("skipped", "box", "keypoints", "reason"),
    [
        (True, [0.0, 0.0, 10.0, 10.0], [[1.0, 2.0, 0.0, 0.9]], "skipped"),
        (False, None, None, "no_box"),
        (False, [0.0, 0.0, 10.0, 10.0], None, "no_pose"),
    ],
)
def test_missing_frames_are_null_with_a_reason(
    skipped: bool, box: list[float] | None, keypoints: list[list[float]] | None, reason: str
) -> None:
    frame = frame_pose(0, 0, skipped, box, keypoints)
    assert frame["keypoints"] is None
    assert frame["missing"] == reason


def test_count_missing() -> None:
    frames = [
        frame_pose(0, 0, False, [0, 0, 1, 1], [[0.0, 0.0, 0.0, 1.0]]),
        frame_pose(1, 100, False, None, None),
        frame_pose(2, 200, True, None, None),
        frame_pose(3, 300, False, [0, 0, 1, 1], None),
    ]
    assert count_missing(frames) == {"found": 1, "skipped": 1, "no_box": 1, "no_pose": 1}


def test_default_config_file_matches_the_defaults() -> None:
    assert load_pose_config(DEFAULT_POSE_CONFIG) == PoseConfig()


@pytest.mark.parametrize(
    "settings",
    [
        {"backend": "openpose"},
        {"model": "../weights/pose.task"},
        {"model": ""},
        {"box_margin": -0.1},
        {"box_margin": 1.5},
        {"min_pose_confidence": 0},
        {"min_pose_confidence": 1},
    ],
)
def test_bad_settings_are_rejected(settings: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        PoseConfig(**settings)  # type: ignore[arg-type]


def test_unknown_keys_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "pose.toml"
    path.write_text("box_margn = 0.2\n")
    with pytest.raises(ValueError, match="box_margn"):
        load_pose_config(path)
