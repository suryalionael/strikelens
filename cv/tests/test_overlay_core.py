"""What the overlay draws, as plain shapes. No OpenCV, no footage."""

import pytest

from strikelens_cv.overlay import (
    SKELETON,
    OverlayConfig,
    confirmed_tags,
    corner_owners,
    corner_shapes,
    frames_to_render,
    id_shapes,
    output_name,
    render_span,
    skeleton_shapes,
    timeline_shapes,
)
from strikelens_cv.overlay.core import BLUE, GREY, JOINTS, RED, WHITE, Label, Line, Rect
from strikelens_cv.pose.core import MEDIAPIPE_LANDMARKS
from strikelens_cv.track.assign import FrameInfo
from tests.track_cases import BLUE_SHORTS, RED_SHORTS, person

CONFIG = OverlayConfig()
LEFT_WRIST = MEDIAPIPE_LANDMARKS.index("left_wrist")


def keypoints(hidden: tuple[int, ...] = ()) -> list[list[float]]:
    """33 keypoints on a diagonal, all visible except `hidden`."""
    return [[i * 10.0, i * 10.0, 0.0, 0.1 if i in hidden else 0.9] for i in range(33)]


class TestSkeleton:
    def test_body_joints_only(self) -> None:
        first_body_joint = MEDIAPIPE_LANDMARKS.index("left_shoulder")
        assert all(first_body_joint <= i < len(MEDIAPIPE_LANDMARKS) for i in JOINTS)

    def test_every_visible_bone_and_joint(self) -> None:
        shapes = skeleton_shapes(keypoints(), RED, 0.5)
        assert sum(isinstance(s, Line) for s in shapes) == len(SKELETON)
        assert len(shapes) == len(SKELETON) + len(JOINTS)

    def test_a_hidden_joint_drops_its_bones(self) -> None:
        shapes = skeleton_shapes(keypoints(hidden=(LEFT_WRIST,)), RED, 0.5)
        wrist = (LEFT_WRIST * 10, LEFT_WRIST * 10)
        assert not any(isinstance(s, Line) and wrist in (s.start, s.end) for s in shapes)
        bones = sum(LEFT_WRIST in bone for bone in SKELETON)
        assert sum(isinstance(s, Line) for s in shapes) == len(SKELETON) - bones


class TestCornerShapes:
    def test_box_and_label_per_corner(self) -> None:
        frame = {"index": 0, "timestamp_ms": 0, "red": [10.0, 50.0, 60.0, 200.0], "blue": None}
        shapes = corner_shapes(frame, {"red": None, "blue": None}, CONFIG)  # type: ignore[arg-type]
        assert shapes == [Rect((10, 50), (60, 200), RED, 2), Label((10, 44), "RED", RED)]

    def test_label_stays_on_screen(self) -> None:
        frame = {"index": 0, "timestamp_ms": 0, "red": None, "blue": [10.0, 2.0, 60.0, 200.0]}
        shapes = corner_shapes(frame, {}, CONFIG)  # type: ignore[arg-type]
        assert Label((10, 14), "BLUE", BLUE) in shapes

    def test_skeleton_drawn_when_keypoints_are_there(self) -> None:
        frame = {"index": 0, "timestamp_ms": 0, "red": [0.0, 0.0, 400.0, 400.0], "blue": None}
        pose = {"index": 0, "timestamp_ms": 0, "box": None, "keypoints": keypoints()}
        missing = {**pose, "keypoints": None, "missing": "no_pose"}
        shapes = corner_shapes(frame, {"red": pose, "blue": missing}, CONFIG)  # type: ignore[dict-item]
        assert len(shapes) == 2 + len(SKELETON) + len(JOINTS)


def frames(skipped: int | None = None) -> list[FrameInfo]:
    return [
        {"index": i, "timestamp_ms": i * 1000, "shot": 0, "skipped": i == skipped}
        for i in range(10)
    ]


ROUNDS = [
    {"number": 1, "start_ms": 1000, "end_ms": 3000},
    {"number": 2, "start_ms": 6000, "end_ms": 8000},
]


class TestFramesToRender:
    def test_one_round(self) -> None:
        chosen = frames_to_render(frames(), ROUNDS, 2)  # type: ignore[arg-type]
        assert [f["index"] for f in chosen] == [6, 7, 8]

    def test_every_round(self) -> None:
        chosen = frames_to_render(frames(), ROUNDS, None)  # type: ignore[arg-type]
        assert [f["index"] for f in chosen] == [1, 2, 3, 6, 7, 8]

    def test_no_rounds_keeps_every_frame_not_skipped(self) -> None:
        chosen = frames_to_render(frames(skipped=5), [], None)
        assert [f["index"] for f in chosen] == [0, 1, 2, 3, 4, 6, 7, 8, 9]

    def test_skipped_frames_inside_a_round_are_left_out(self) -> None:
        chosen = frames_to_render(frames(skipped=7), ROUNDS, 2)  # type: ignore[arg-type]
        assert [f["index"] for f in chosen] == [6, 8]

    def test_unknown_round(self) -> None:
        with pytest.raises(ValueError, match="no round 3"):
            frames_to_render(frames(), ROUNDS, 3)  # type: ignore[arg-type]


def test_render_span() -> None:
    assert render_span(frames(), ROUNDS, 2) == (6000, 8000)  # type: ignore[arg-type]
    assert render_span(frames()[2:5], ROUNDS, None) == (2000, 4000)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("round_number", "ids", "name"),
    [
        (None, False, "overlay.mp4"),
        (2, False, "overlay-round-2.mp4"),
        (None, True, "overlay-ids.mp4"),
        (1, True, "overlay-ids-round-1.mp4"),
    ],
)
def test_output_name(round_number: int | None, ids: bool, name: str) -> None:
    assert output_name(round_number, ids) == name


def test_only_confirmed_tags() -> None:
    tags = [{"status": s, "timestamp_ms": 0} for s in ("confirmed", "pending", "rejected")]
    assert confirmed_tags(tags) == [tags[0]]


class TestTimeline:
    # A 101-pixel strip under a 200-pixel picture: 1 pixel per 10 ms over 0-1000 ms.
    def _shapes(self, tags: list[dict[str, object]], now_ms: int = 0) -> list[object]:
        rounds = [{"number": 1, "start_ms": 0, "end_ms": 1000}]
        return timeline_shapes(tags, rounds, (0, 1000), now_ms, 101, 200, 40)  # type: ignore[arg-type,return-value]

    def test_background_centre_line_and_round_marks(self) -> None:
        shapes = self._shapes([])
        assert shapes[:2] == [
            Rect((0, 200), (100, 239), (30, 30, 30), -1),
            Line((0, 220), (100, 220), GREY, 1),
        ]
        assert Line((0, 204), (0, 235), GREY, 1) in shapes
        assert Line((100, 204), (100, 235), GREY, 1) in shapes

    def test_red_ticks_above_blue_below(self) -> None:
        shapes = self._shapes(
            [{"timestamp_ms": 500, "fighter": "red"}, {"timestamp_ms": 250, "fighter": "blue"}]
        )
        assert Line((50, 218), (50, 206), RED) in shapes
        assert Line((25, 222), (25, 233), BLUE) in shapes

    def test_tags_outside_the_span_are_left_out(self) -> None:
        shapes = self._shapes([{"timestamp_ms": 1500, "fighter": "red"}])
        assert not any(isinstance(s, Line) and s.colour == RED for s in shapes)

    def test_playhead(self) -> None:
        assert self._shapes([], now_ms=1000)[-1] == Line((100, 200), (100, 239), WHITE)


def test_id_shapes_colour_by_corner() -> None:
    detections = (
        person(3, 1, range(1), 50, RED_SHORTS)
        + person(3, 2, range(1), 400, BLUE_SHORTS)
        + person(3, 9, range(1), 250, 0)
    )
    owners = corner_owners(
        [{"shot": 3, "red": [1], "blue": [2], "dropped": [9], "uncertain": False}]  # type: ignore[typeddict-item]
    )
    assert owners == {(3, 1): "red", (3, 2): "blue"}
    shapes = id_shapes(detections, owners)
    labels = [s for s in shapes if isinstance(s, Label)]
    assert [(s.text, s.colour) for s in labels] == [
        ("s3 t1", RED),
        ("s3 t2", BLUE),
        ("s3 t9", GREY),
    ]
