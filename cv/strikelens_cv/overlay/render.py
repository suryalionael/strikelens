"""Render the overlay video for one fight: files in, an MP4 out.

Reads the ingest, track, and pose output, draws the shapes from core.py with
OpenCV, and pipes the frames into FFmpeg for an H.264 MP4 that plays in browsers
and on phones. Needs FFmpeg and the `ingest` extra (OpenCV). Every input is read
and checked before OpenCV is imported, so missing files fail fast.
"""

import json
import subprocess
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from strikelens_cv.ingest.frames import ffmpeg_binary
from strikelens_cv.overlay.config import OverlayConfig
from strikelens_cv.overlay.core import (
    Dot,
    Label,
    Line,
    Rect,
    Shape,
    confirmed_tags,
    corner_owners,
    corner_shapes,
    credit_shape,
    frames_to_render,
    id_shapes,
    output_name,
    render_span,
    timeline_shapes,
)
from strikelens_cv.paths import processed_dir
from strikelens_cv.pose.core import CORNERS, Corner, FramePose
from strikelens_cv.segments import Round, load_rounds
from strikelens_cv.track.assign import Detection


@dataclass(frozen=True)
class OverlayResult:
    path: Path
    frames: int
    tags: int
    rounds: list[Round]
    keypoints: bool  # False when keypoints/ was missing, so no skeletons were drawn


def _read(path: Path, hint: str) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found; {hint}")
    return json.loads(path.read_text())


def _poses(path: Path) -> dict[int, FramePose] | None:
    if not path.is_file():
        return None
    return {f["index"]: f for f in json.loads(path.read_text())["frames"]}


def draw(canvas: Any, shapes: Sequence[Shape]) -> None:
    """Draw shapes onto a BGR image in place."""
    import cv2

    for s in shapes:
        if isinstance(s, Rect):
            cv2.rectangle(canvas, s.top_left, s.bottom_right, s.colour, s.thickness)
        elif isinstance(s, Line):
            cv2.line(canvas, s.start, s.end, s.colour, s.thickness, cv2.LINE_AA)
        elif isinstance(s, Dot):
            cv2.circle(canvas, s.centre, s.radius, s.colour, -1, cv2.LINE_AA)
        elif isinstance(s, Label):
            # A dark outline first, so the text reads on any background.
            for colour, thickness in (((0, 0, 0), 3), (s.colour, 1)):
                cv2.putText(
                    canvas,
                    s.text,
                    s.at,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    s.scale,
                    colour,
                    thickness,
                    cv2.LINE_AA,
                )


def encoder_command(
    ffmpeg: str, width: int, height: int, fps: float, crf: int, out: Path
) -> list[str]:
    """FFmpeg reading raw BGR frames on stdin and writing H.264 in yuv420p."""
    return [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{width}x{height}",
        "-r",
        f"{fps:g}",
        "-i",
        "-",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        str(crf),
        "-movflags",
        "+faststart",
        str(out),
    ]


def overlay(
    fight: str, config: OverlayConfig, round_number: int | None = None, ids: bool = False
) -> OverlayResult:
    """Render one fight, one round of it, or its track IDs into data/processed/<fight>/."""
    out_dir = processed_dir(fight)
    manifest = _read(out_dir / "frames.json", "run strikelens-cv ingest first")
    labelled = _read(out_dir / "detections.json", "run strikelens-cv track first")
    tracks = _read(out_dir / "tracks.json", "run strikelens-cv track first")
    fight_json = out_dir / "fight.json"
    rounds = load_rounds(fight_json) if fight_json.is_file() else []
    tags_file = out_dir / "tags.json"
    tags = confirmed_tags(json.loads(tags_file.read_text())) if tags_file.is_file() else []
    poses = {corner: _poses(out_dir / "keypoints" / f"{corner}.json") for corner in CORNERS}

    frames = frames_to_render(labelled["frames"], rounds, round_number)
    if not frames:
        raise ValueError("no frames to render: every frame is skipped or outside the rounds")
    span = render_span(frames, rounds, round_number)
    files = {f["index"]: f["file"] for f in manifest["frames"]}
    by_index = {f["index"]: f for f in tracks["frames"]}
    owners = corner_owners(tracks["shots"])
    detections: dict[int, list[Detection]] = defaultdict(list)
    for d in labelled["detections"]:
        detections[d["frame"]].append(d)
    out = out_dir / output_name(round_number, ids)

    try:
        import cv2
        import numpy as np
    except ImportError as error:
        raise RuntimeError(
            "The overlay needs the ingest extra: cd cv && uv sync --extra ingest"
        ) from error

    def image(index: int) -> Any:
        picture = cv2.imread(str(out_dir / "frames" / files[index]))
        if picture is None:
            raise FileNotFoundError(f"cannot read frame {files[index]}")
        return picture

    height, width = image(frames[0]["index"]).shape[:2]
    # yuv420p needs an even width and height.
    out_width = width - width % 2
    out_height = height + config.timeline_height
    out_height -= out_height % 2

    command = encoder_command(
        ffmpeg_binary(), out_width, out_height, manifest["fps"], config.crf, out
    )
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert encoder.stdin is not None
    try:
        for frame in frames:
            picture = image(frame["index"])
            if picture.shape[:2] != (height, width):
                picture = cv2.resize(picture, (width, height))
            canvas = np.zeros((out_height, out_width, 3), dtype=np.uint8)
            canvas[:height, :out_width] = picture[:, :out_width]
            if ids:
                shapes = id_shapes(detections[frame["index"]], owners)
            else:
                now: dict[Corner, FramePose | None] = {
                    c: (p.get(frame["index"]) if p else None) for c, p in poses.items()
                }
                track_frame = by_index.get(frame["index"])
                shapes = corner_shapes(track_frame, now, config) if track_frame else []
            shapes.append(credit_shape(config.credit))
            shapes += timeline_shapes(
                tags,
                rounds,
                span,
                frame["timestamp_ms"],
                out_width,
                height,
                out_height - height,
            )
            draw(canvas, shapes)
            encoder.stdin.write(canvas.tobytes())
    finally:
        encoder.stdin.close()
        code = encoder.wait()
    if code != 0:
        raise RuntimeError(f"FFmpeg could not write {out} (exit code {code})")
    return OverlayResult(
        path=out,
        frames=len(frames),
        tags=len(tags),
        rounds=rounds,
        keypoints=all(p is not None for p in poses.values()),
    )
