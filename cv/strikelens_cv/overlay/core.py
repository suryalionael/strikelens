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
from strikelens_cv.segments import Round, Segment, in_round, in_segment
from strikelens_cv.track.assign import Detection, FrameInfo, ShotResult, TrackFrame

Colour = tuple[int, int, int]  # B, G, R, as OpenCV draws
Point = tuple[int, int]

RED: Colour = (40, 40, 230)
BLUE: Colour = (230, 120, 30)
GREY: Colour = (170, 170, 170)
WHITE: Colour = (255, 255, 255)
GREEN: Colour = (110, 210, 110)
BLACK: Colour = (0, 0, 0)
STRIP: Colour = (30, 30, 30)
CORNER_COLOURS: dict[Corner, Colour] = {"red": RED, "blue": BLUE}


@dataclass(frozen=True)
class Rect:
    top_left: Point
    bottom_right: Point
    colour: Colour
    thickness: int = 2  # -1 fills it
    alpha: float = 1.0  # below 1, a filled rectangle is see-through


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


# The stat panel and strike flashes (#22). Layout after mma-vision's broadcast panel
# by Binyam Abraha (ADR 0011). Counts follow the API's stats: confirmed tags inside a
# round and outside replays and non-fight segments (docs/stat-definitions.md).

PANEL_ORIGIN: Point = (16, 40)  # under the credit line
PANEL_HEIGHT_REF = 720  # the panel is laid out for a 720 px high frame, and scaled
PANEL_SIZE: Point = (330, 126)


def counted_tags(
    tags: Iterable[Mapping[str, Any]], rounds: Sequence[Round], segments: Sequence[Segment]
) -> list[Mapping[str, Any]]:
    """Tags that count toward the stats: confirmed, inside a round, not in a segment."""
    return [
        t
        for t in tags
        if t.get("status") == "confirmed"
        and in_round(t["timestamp_ms"], rounds)
        and not in_segment(t["timestamp_ms"], segments)
    ]


def running_counts(tags: Sequence[Mapping[str, Any]], now_ms: int) -> dict[Corner, tuple[int, int]]:
    """(thrown, landed) per corner over the counted tags at or before `now_ms`."""
    out: dict[Corner, tuple[int, int]] = {}
    for corner in CORNERS:
        mine = [t for t in tags if t["fighter"] == corner and t["timestamp_ms"] <= now_ms]
        out[corner] = (len(mine), sum(1 for t in mine if t.get("outcome") == "landed"))
    return out


def accuracy_text(thrown: int, landed: int) -> str:
    """Landed over thrown as a whole percent; "--" when nothing was thrown, never 0%."""
    return "--" if thrown == 0 else f"{round(100 * landed / thrown)}%"


def round_clock(rounds: Sequence[Round], now_ms: int) -> tuple[int, int] | None:
    """(round number, time into it) at `now_ms`. Between rounds the clock holds at the
    end of the round before. None before the first round."""
    started = [r for r in sorted(rounds, key=lambda r: r["start_ms"]) if r["start_ms"] <= now_ms]
    if not started:
        return None
    current = started[-1]
    return current["number"], min(now_ms, current["end_ms"]) - current["start_ms"]


def clock_text(ms: int) -> str:
    seconds = max(ms, 0) // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"


def stat_panel_shapes(
    counts: Mapping[Corner, tuple[int, int]],
    clock: tuple[int, int] | None,
    names: Mapping[Corner, str],
    alpha: float,
    scale: float = 1.0,
) -> list[Shape]:
    """A see-through panel: round and clock, then thrown, landed, and accuracy per
    fighter, and a footer saying where the counts come from. `scale` sizes it for
    the frame (1.0 for 720 px high)."""

    def p(dx: float, dy: float) -> Point:
        return _point(PANEL_ORIGIN[0] + dx * scale, PANEL_ORIGIN[1] + dy * scale)

    def text(dx: float, dy: float, s: str, colour: Colour, size: float) -> Label:
        return Label(p(dx, dy), s, colour, size * scale)

    w, h = PANEL_SIZE
    header = "STRIKELENS" if clock is None else f"ROUND {clock[0]}"
    shapes: list[Shape] = [
        Rect(p(0, 0), p(w, h), BLACK, -1, alpha),
        text(10, 20, header, WHITE, 0.5),
    ]
    if clock is not None:
        shapes.append(text(w - 52, 20, clock_text(clock[1]), WHITE, 0.5))
    shapes += [
        text(150, 42, "THROWN", GREY, 0.4),
        text(212, 42, "LANDED", GREY, 0.4),
        text(280, 42, "ACC", GREY, 0.4),
    ]
    for row, corner in enumerate(CORNERS):
        thrown, landed = counts.get(corner, (0, 0))
        top = 64 + row * 24
        shapes += [
            Rect(p(10, top - 13), p(16, top + 3), CORNER_COLOURS[corner], -1),
            text(24, top, names.get(corner, corner.upper())[:16], WHITE, 0.5),
            text(160, top, f"{thrown:>3}", WHITE, 0.5),
            text(222, top, f"{landed:>3}", GREEN, 0.5),
            text(276, top, f"{accuracy_text(thrown, landed):>4}", WHITE, 0.5),
        ]
    shapes.append(text(10, h - 10, "Counts: analyst-confirmed tags", GREY, 0.38))
    return shapes


def strike_label(tag: Mapping[str, Any]) -> str:
    """KICK / LANDED / BODY: weapon, outcome, and target, leaving out any not set."""
    parts = [str(tag[f]).upper() for f in ("weapon", "outcome", "target") if tag.get(f)]
    return " / ".join(parts) or "STRIKE"


def flash_shapes(
    tags: Sequence[Mapping[str, Any]],
    frame: TrackFrame | None,
    now_ms: int,
    flash_ms: int,
    scale: float = 1.0,
) -> list[Shape]:
    """For `flash_ms` after each counted tag, its label above that fighter's box. A
    fighter without a box in this frame gets no label (there is nowhere to put it)."""
    shapes: list[Shape] = []
    stacked: dict[Corner, int] = {}
    for tag in sorted(tags, key=lambda t: -t["timestamp_ms"]):
        age = now_ms - tag["timestamp_ms"]
        corner: Corner = tag["fighter"]
        box = frame[corner] if frame is not None else None
        if not 0 <= age <= flash_ms or box is None:
            continue
        level = stacked.get(corner, 0)
        stacked[corner] = level + 1
        at = _point(box[0], max(box[1] - (30 + 22 * level) * scale, 40 * scale))
        shapes.append(Label(at, strike_label(tag), CORNER_COLOURS[corner], 0.7 * scale))
    return shapes
