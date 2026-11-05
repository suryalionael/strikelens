"""Camera cut detection with PySceneDetect."""

from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict

from strikelens_cv.ingest.config import IngestConfig


class Shot(TypedDict):
    index: int
    start_ms: int
    end_ms: int


def shots_from_scenes(
    scenes: Sequence[tuple[float, float]], duration_ms: int, min_shot_ms: int
) -> list[Shot]:
    """Shots from (start, end) scene times in seconds.

    No scenes means no cut was found, so the whole video is one shot. A shot shorter
    than `min_shot_ms` is merged into the shot before it (or after it, if it is the
    first), so a flash is not reported as a cut.
    """
    spans = [(round(start * 1000), round(end * 1000)) for start, end in scenes]
    if not spans:
        spans = [(0, duration_ms)]
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if not merged:
            merged.append((start, end))
            continue
        this_is_short = end - start < min_shot_ms
        # Only the first shot can still be short here; later short ones were merged.
        previous_is_short = merged[-1][1] - merged[-1][0] < min_shot_ms
        if this_is_short or previous_is_short:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return [{"index": i, "start_ms": s, "end_ms": e} for i, (s, e) in enumerate(merged)]


def cut_times_ms(shots: Sequence[Shot]) -> list[int]:
    """The moments the camera cuts: every shot start after the first."""
    return [shot["start_ms"] for shot in shots[1:]]


def detect_scenes(video: Path, config: IngestConfig) -> tuple[list[tuple[float, float]], int]:
    """Run PySceneDetect. Returns scene times in seconds and the video length in ms."""
    try:
        from scenedetect import ContentDetector, SceneManager, open_video
    except ImportError as error:
        raise RuntimeError(
            "Cut detection needs the ingest extra: cd cv && uv sync --extra ingest"
        ) from error

    stream = open_video(str(video))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=config.cut_threshold))
    manager.detect_scenes(stream)
    scenes = [(start.seconds, end.seconds) for start, end in manager.get_scene_list()]
    duration_ms = round(stream.duration.seconds * 1000) if stream.duration else 0
    return scenes, duration_ms
