"""Pure overlay logic: which frames to render, and what to draw on each of them.

Everything here returns plain shapes (rectangles, lines, dots, labels) in pixel
coordinates. No OpenCV, so CI tests all of it. render.py turns the shapes into
pixels and pipes the frames into FFmpeg.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from strikelens_cv.overlay.config import OverlayConfig
from strikelens_cv.pose.core import CORNERS, MEDIAPIPE_LANDMARKS, Corner, FramePose, Keypoint
from strikelens_cv.segments import Round, in_round
from strikelens_cv.track.assign import Detection, FrameInfo, ShotResult, TrackFrame

Colour = tuple[int, int, int]  # B, G, R, as OpenCV draws
Point = tuple[int, int]

RED: Colour = (40, 40, 230)
BLUE: Colour = (230, 120, 30)
GREY: Colour = (170, 170, 170)
WHITE: Colour = (255, 255, 255)
STRIP: Colour = (30, 30, 30)
CORNER_COLOURS: dict[Corner, Colour] = {"red": RED, "blue": BLUE}


@dataclass(frozen=True)
class Rect:
    top_left: Point
    bottom_right: Point
    colour: Colour
    thickness: int = 2  # -1 fills it


@dataclass(frozen=True)
class Line:
    start: Point
    end: Point
    colour: Colour
    thickness: int = 2


@dataclass(frozen=True)
class Dot:
    centre: Point
    radius: int
    colour: Colour


@dataclass(frozen=True)
class Label:
    at: Point  # bottom left of the text
    text: str
    colour: Colour
    scale: float = 0.5


Shape = Rect | Line | Dot | Label


def _bone(a: str, b: str) -> tuple[int, int]:
    return MEDIAPIPE_LANDMARKS.index(a), MEDIAPIPE_LANDMARKS.index(b)


# MediaPipe's body connections: torso, arms, and legs. Face and finger points are
# left out; at broadcast distance they are a blur of dots.
SKELETON: tuple[tuple[int, int], ...] = tuple(
    _bone(a, b)
    for a, b in (
        ("left_shoulder", "right_shoulder"),
        ("left_shoulder", "left_hip"),
        ("right_shoulder", "right_hip"),
        ("left_hip", "right_hip"),
        ("left_shoulder", "left_elbow"),
        ("left_elbow", "left_wrist"),
        ("right_shoulder", "right_elbow"),
        ("right_elbow", "right_wrist"),
        ("left_hip", "left_knee"),
        ("left_knee", "left_ankle"),
        ("left_ankle", "left_heel"),
        ("left_heel", "left_foot_index"),
        ("left_ankle", "left_foot_index"),
        ("right_hip", "right_knee"),
        ("right_knee", "right_ankle"),
        ("right_ankle", "right_heel"),
        ("right_heel", "right_foot_index"),
        ("right_ankle", "right_foot_index"),
    )
)
JOINTS: tuple[int, ...] = tuple(sorted({i for bone in SKELETON for i in bone}))


def _point(x: float, y: float) -> Point:
    return round(x), round(y)


# Which frames, and over what time span


def frames_to_render(
    frames: Sequence[FrameInfo], rounds: Sequence[Round], round_number: int | None
) -> list[FrameInfo]:
    """Frames for the video: not skipped, and inside the chosen round or any round.

    Without rounds every frame that was not skipped is kept, as `track` does.
    """
    chosen = list(rounds)
    if round_number is not None:
        chosen = [r for r in rounds if r["number"] == round_number]
        if not chosen:
            raise ValueError(f"no round {round_number} in fight.json")
    return [
        f
        for f in frames
        if not f["skipped"] and (not chosen or in_round(f["timestamp_ms"], chosen))
    ]


def render_span(
    frames: Sequence[FrameInfo], rounds: Sequence[Round], round_number: int | None
) -> tuple[int, int]:
    """The time span the timeline covers: the chosen round, or first to last frame."""
    for r in rounds:
        if r["number"] == round_number:
            return r["start_ms"], r["end_ms"]
    if not frames:
        raise ValueError("no frames to render")
    return frames[0]["timestamp_ms"], frames[-1]["timestamp_ms"]


def output_name(round_number: int | None, ids: bool) -> str:
    """overlay.mp4, overlay-round-2.mp4, overlay-ids.mp4, or overlay-ids-round-2.mp4."""
    parts = ["overlay"] + (["ids"] if ids else [])
    if round_number is not None:
        parts += ["round", str(round_number)]
    return "-".join(parts) + ".mp4"


# What to draw on the picture


def skeleton_shapes(
    keypoints: Sequence[Keypoint], colour: Colour, min_visibility: float
) -> list[Shape]:
    """Bones between visible body joints, then a dot on each visible joint."""
    visible = {i for i in JOINTS if i < len(keypoints) and keypoints[i][3] >= min_visibility}
    shapes: list[Shape] = [
        Line(_point(*keypoints[a][:2]), _point(*keypoints[b][:2]), colour)
        for a, b in SKELETON
        if a in visible and b in visible
    ]
    shapes += [Dot(_point(*keypoints[i][:2]), 3, colour) for i in sorted(visible)]
    return shapes


def _labelled_box(box: Sequence[float], text: str, colour: Colour, thickness: int) -> list[Shape]:
    return [
        Rect(_point(box[0], box[1]), _point(box[2], box[3]), colour, thickness),
        Label(_point(box[0], max(box[1] - 6, 14)), text, colour),
    ]


def corner_shapes(
    frame: TrackFrame, poses: Mapping[Corner, FramePose | None], config: OverlayConfig
) -> list[Shape]:
    """The red and blue box, each with its corner name and skeleton."""
    shapes: list[Shape] = []
    for corner in CORNERS:
        colour = CORNER_COLOURS[corner]
        box = frame[corner]
        if box is not None:
            shapes += _labelled_box(box, corner.upper(), colour, 2)
        pose = poses.get(corner)
        if pose is not None and pose["keypoints"] is not None:
            shapes += skeleton_shapes(pose["keypoints"], colour, config.min_visibility)
    return shapes


def corner_owners(shots: Iterable[ShotResult]) -> dict[tuple[int, int], Corner]:
    """(shot, track ID) -> corner, from the per-shot results in tracks.json."""
    return {
        (result["shot"], track_id): corner
        for result in shots
        for corner in CORNERS
        for track_id in result[corner]
    }


def id_shapes(
    detections: Iterable[Detection], owners: Mapping[tuple[int, int], Corner]
) -> list[Shape]:
    """Every detected person, labelled with shot and track ID, for writing corrections.

    Tracks assigned to a corner are drawn in its colour; everyone else in grey.
    """
    shapes: list[Shape] = []
    for d in detections:
        corner = owners.get((d["shot"], d["track_id"]))
        colour = CORNER_COLOURS[corner] if corner else GREY
        shapes += _labelled_box(d["box"], f"s{d['shot']} t{d['track_id']}", colour, 2)
    return shapes


def credit_shape(text: str) -> Label:
    return Label((10, 24), text, WHITE)


# The strike timeline under the picture


def confirmed_tags(tags: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Only confirmed tags go on the timeline, whatever else the file holds."""
    return [t for t in tags if t.get("status") == "confirmed"]


def timeline_shapes(
    tags: Sequence[Mapping[str, Any]],
    rounds: Sequence[Round],
    span: tuple[int, int],
    now_ms: int,
    width: int,
    top: int,
    height: int,
) -> list[Shape]:
    """The strip under the picture.

    A centre line for the time span, a grey mark at each round start and end, a
    tick per confirmed tag (red above the line, blue below), and a white playhead.
    """
    start, end = span
    length = max(end - start, 1)
    right = width - 1
    bottom = top + height - 1
    middle = top + height // 2

    def x(ms: int) -> int:
        return round(min(max(ms - start, 0), length) / length * right)

    shapes: list[Shape] = [
        Rect((0, top), (right, bottom), STRIP, -1),
        Line((0, middle), (right, middle), GREY, 1),
    ]
    for r in rounds:
        for ms in (r["start_ms"], r["end_ms"]):
            if start <= ms <= end:
                shapes.append(Line((x(ms), top + 4), (x(ms), bottom - 4), GREY, 1))
    for tag in tags:
        ms = tag["timestamp_ms"]
        if not start <= ms <= end:
            continue
        if tag["fighter"] == "red":
            shapes.append(Line((x(ms), middle - 2), (x(ms), top + 6), RED))
        else:
            shapes.append(Line((x(ms), middle + 2), (x(ms), bottom - 6), BLUE))
    shapes.append(Line((x(now_ms), top), (x(now_ms), bottom), WHITE))
    return shapes
